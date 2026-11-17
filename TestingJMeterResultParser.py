import csv
import tempfile
import unittest
from pathlib import Path

from DateTimeBucketManager import DateTimeBucketManager
from JMeterResultParser import process_file
from SampleCollection import SampleCollection


class TestJMeterResultParser(unittest.TestCase):
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
