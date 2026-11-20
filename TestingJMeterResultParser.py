import csv
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from DateTimeBucketManager import DateTimeBucketManager
from PassFailCriteria import (
    PassFailCriteria,
    get_pass_fail_criteria_collection_from_json,
)
from JMeterResultParser import (
    get_bucket_stats_lists,
    get_overall_metrics_and_execute_threshold_analysis,
    get_overall_stats_list,
    process_file,
    str_to_bool,
)
from SampleCollection import SampleCollection


class TestJMeterResultParser(unittest.TestCase):
    @staticmethod
    def create_rollup():
        return SimpleNamespace(
            total_count=2,
            success_count=1,
            error_count=1,
            min_ms=3.0,
            max_ms=30.0,
            calc_error_rate=Mock(return_value=50.0),
            calc_items_per_second=Mock(return_value=1.25),
            calc_avg_elapsed_ms=Mock(return_value=5.25),
            perc_50=3.0,
            perc_75=4.0,
            perc_90=6.0,
            perc_95=8.0,
        )

    def test_get_pass_fail_criteria_collection_builds_criteria_from_json(self):
        PassFailCriteria.set_valid_metric_list(["avg_elapsed_ms"])
        try:
            criteria_collection = get_pass_fail_criteria_collection_from_json(
                '{"pass_fail_criteria_list": ['
                '{"label": "Search", "metric": "avg_elapsed_ms", '
                '"operator": "<", "threshold_value": 22.0}]}'
            )
        finally:
            PassFailCriteria.set_valid_metric_list([])

        criteria = criteria_collection.pf_criteria_dict["Search_avg_elapsed_ms"]
        self.assertEqual(
            (criteria.label, criteria.metric, criteria.operator, criteria.threshold_value),
            ("Search", "avg_elapsed_ms", "<", 22.0),
        )

    def test_process_file_uses_csv_columns_and_preserves_quoted_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "results.csv"
            with input_path.open("w", encoding="utf-8", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["JMeter results"])
                writer.writerow(["success", "label", "timeStamp", "elapsed"])
                writer.writerow(["true", "Search, users", "1762610533000", "42"])

            buckets = DateTimeBucketManager(1)
            samples = SampleCollection()
            process_file(input_path, buckets, samples)

        self.assertEqual(samples.label_list, ["Search, users"])
        self.assertEqual(
            samples.get_overall_rollup_sample("Search, users").elapsed_ms, 42.0
        )
        self.assertEqual(
            samples.get_overall_rollup_sample("Search, users").success_count, 1
        )

    def test_process_file_reports_missing_required_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "results.csv"
            input_path.write_text("timeStamp,label\n1,request\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Could not find the required headers"):
                process_file(
                    input_path,
                    DateTimeBucketManager(1),
                    SampleCollection(),
                )

    def test_process_file_reports_invalid_data_line_number(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "results.csv"
            input_path.write_text(
                "JMeter results\n"
                "success,label,timeStamp,elapsed\n"
                "true,request,1762610533000,not-a-number\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "Invalid data on CSV line 3"):
                process_file(
                    input_path,
                    DateTimeBucketManager(1),
                    SampleCollection(),
                )

    def test_str_to_bool_recognizes_supported_true_values(self):
        for value in ("true", " YES ", "y", "1", "T"):
            with self.subTest(value=value):
                self.assertTrue(str_to_bool(value))

        for value in ("false", "no", "0", ""):
            with self.subTest(value=value):
                self.assertFalse(str_to_bool(value))

    def test_overall_metrics_map_rollup_values_and_threshold_results(self):
        rollup = self.create_rollup()
        criteria_collection = Mock()

        def evaluate_threshold(label, metric, value):
            if metric == "err_perc":
                return True, False, "threshold failed\n", ""
            if metric == "avg_elapsed_ms":
                return True, True, "", "threshold passed\n"
            return False, False, "", ""

        criteria_collection.find_and_execute_pass_fail_criteria_and_return_success.side_effect = (
            evaluate_threshold
        )

        metrics, failures, passes = get_overall_metrics_and_execute_threshold_analysis(
            "Search", criteria_collection, rollup
        )

        self.assertEqual(
            metrics,
            [
                2,
                1,
                1,
                50.0,
                3.0,
                30.0,
                1.25,
                5.25,
                3.0,
                4.0,
                6.0,
                8.0,
            ],
        )
        self.assertEqual(failures, ["threshold failed\n"])
        self.assertEqual(passes, ["threshold passed\n"])
        threshold_calls = (
            criteria_collection.find_and_execute_pass_fail_criteria_and_return_success.call_args_list
        )
        self.assertEqual(
            [(call.args[1], call.args[2]) for call in threshold_calls],
            list(
                zip(
                    [
                        "tot_count",
                        "succ_count",
                        "err_count",
                        "err_perc",
                        "min_ms",
                        "max_ms",
                        "trans_per_sec",
                        "avg_elapsed_ms",
                        "50th_%_elapsed_ms",
                        "75th_%_elapsed_ms",
                        "90th_%_elapsed_ms",
                        "95th_%_elapsed_ms",
                    ],
                    metrics,
                )
            ),
        )

    def test_overall_stats_format_floats_to_two_places_and_preserve_counts(self):
        sample_collection = Mock()
        sample_collection.get_overall_rollup_sample.return_value = self.create_rollup()
        criteria_collection = Mock()
        criteria_collection.find_and_execute_pass_fail_criteria_and_return_success.return_value = (
            False,
            False,
            "",
            "",
        )

        lines, failures, passes = get_overall_stats_list(
            ["Search"], sample_collection, criteria_collection
        )

        self.assertEqual(
            lines[1],
            "Search,2,1,1,50.00,3.00,30.00,1.25,5.25,3.00,4.00,6.00,8.00\n",
        )
        self.assertEqual(failures, [])
        self.assertEqual(passes, [])

    def test_bucket_stats_format_parser_report_sections(self):
        sample_collection = Mock()
        sample_collection.get_bucket_stats.return_value = (
            [2, 0],
            [10.5, 0.0],
            [0.25, 0.0],
        )

        datetime_strings = ["2025-11-08 14:02:00", "2025-11-08 14:03:00"]
        total_lines, average_lines, rate_lines = get_bucket_stats_lists(
            datetime_strings,
            ["2025-11-08 14:02", "2025-11-08 14:03"],
            ["Search"],
            sample_collection,
        )

        self.assertEqual(total_lines[1], "Search,2,0\n")
        self.assertEqual(average_lines[1], "Search,10.50,0.00\n")
        self.assertEqual(rate_lines[1], "Search,0.25,0.00\n")
        sample_collection.get_bucket_stats.assert_called_once_with(
            datetime_strings, "Search"
        )
