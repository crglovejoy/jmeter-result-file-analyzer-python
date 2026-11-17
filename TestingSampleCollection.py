import unittest
from types import MappingProxyType

from Sample import RollupSample, Sample
from SampleCollection import (
    BUCKET_SUMMARY_LABEL_PREFIX,
    OVERALL_SUMMARY_LABEL_PREFIX,
    SampleCollection,
)


class TestSampleCollection(unittest.TestCase):
    def test_collection_starts_empty(self):
        collection = SampleCollection()

        self.assertEqual(collection.label_list, [])
        self.assertEqual(dict(collection.sample_dict), {})

    def test_adding_samples_updates_raw_and_rollup_samples(self):
        collection = SampleCollection()
        collection.add_sample("bucket1", "request", True, 10)
        collection.add_sample("bucket1", "request", False, 30)
        collection.add_sample("bucket2", "request", True, 20)

        samples = collection.sample_dict
        self.assertEqual(collection.label_list, ["request"])
        self.assertEqual(
            [sample.elapsed_ms for sample in samples["bucket1_request"]],
            [10.0, 30.0],
        )
        self.assertIsInstance(samples["bucket1_request"][0], Sample)
        self.assertEqual(
            [sample.elapsed_ms for sample in samples["bucket2_request"]], [20.0]
        )

        bucket1_rollup = samples[f"bucket1_{BUCKET_SUMMARY_LABEL_PREFIX}_request"]
        self.assertIsInstance(bucket1_rollup, RollupSample)
        self.assertEqual(bucket1_rollup.total_count, 2)
        self.assertEqual(bucket1_rollup.elapsed_ms, 40.0)
        self.assertEqual(bucket1_rollup.success_count, 1)
        self.assertEqual(bucket1_rollup.success_elapsed_ms, 10.0)

        overall_rollup = collection.get_overall_rollup_sample("request")
        self.assertEqual(
            overall_rollup.total_count, 3
        )
        self.assertEqual(overall_rollup.elapsed_ms, 60.0)
        self.assertEqual(overall_rollup.success_count, 2)
        self.assertEqual(overall_rollup.success_elapsed_ms, 30.0)
        self.assertEqual(overall_rollup.error_count, 1)
        self.assertIn(f"{OVERALL_SUMMARY_LABEL_PREFIX}_request", samples)

    def test_rollup_generation_and_bucket_statistics(self):
        collection = SampleCollection()
        collection.add_sample("bucket1", "request", True, 10)
        collection.add_sample("bucket2", "request", False, 30)
        collection.add_sample("bucket1", "other", False, 40)
        collection.add_sample("bucket2", "other", True, 50)

        collection.generate_rollup_metrics(
            ["bucket1", "bucket2"],
            first_bucket_consumed_secs=10,
            last_bucket_consumed_secs=30,
            standard_bucket_secs=20,
            total_consumed_secs=40,
        )

        request_rollup = collection.get_overall_rollup_sample("request")
        self.assertEqual(request_rollup.consumed_secs, 40.0)
        self.assertEqual(request_rollup.perc_50, 20.0)
        self.assertEqual(request_rollup.perc_75, 25.0)
        self.assertEqual(request_rollup.perc_90, 28.0)
        self.assertEqual(request_rollup.perc_95, 29.0)

        bucket_stats = collection.get_bucket_stats(["bucket1", "bucket2"], "request")
        self.assertEqual(bucket_stats[0], [1, 1])
        self.assertEqual(bucket_stats[1], [10.0, 30.0])
        self.assertEqual(bucket_stats[2], [0.1, 1 / 30])

        other_rollup = collection.get_overall_rollup_sample("other")
        self.assertEqual(other_rollup.perc_50, 45.0)
        self.assertEqual(other_rollup.perc_75, 47.5)
        self.assertEqual(other_rollup.perc_90, 49.0)
        self.assertEqual(other_rollup.perc_95, 49.5)

    def test_sample_dict_is_read_only_and_label_list_is_a_copy(self):
        collection = SampleCollection()
        collection.add_sample("bucket1", "request", True, 10)

        self.assertIsInstance(collection.sample_dict, MappingProxyType)
        with self.assertRaises(TypeError):
            collection.sample_dict["extra"] = []

        labels = collection.label_list
        labels.append("extra")
        self.assertEqual(collection.label_list, ["request"])

    def test_bucket_stats_use_zeros_for_missing_buckets(self):
        collection = SampleCollection()
        collection.add_sample("bucket1", "request", True, 10)

        self.assertEqual(
            collection.get_bucket_stats(["bucket1", "missing"], "request"),
            ([1, 0], [10.0, 0.0], [0.0, 0.0]),
        )

    def test_rollup_generation_uses_bucket_count_not_label_count(self):
        collection = SampleCollection()
        prefixes = ["bucket1", "bucket2", "bucket3"]
        for prefix in prefixes:
            collection.add_sample(prefix, "request", True, 10)

        collection.generate_rollup_metrics(
            prefixes,
            first_bucket_consumed_secs=5,
            last_bucket_consumed_secs=15,
            standard_bucket_secs=10,
            total_consumed_secs=30,
        )

        self.assertEqual(
            [
                collection.sample_dict[
                    f"{prefix}_{BUCKET_SUMMARY_LABEL_PREFIX}_request"
                ].consumed_secs
                for prefix in prefixes
            ],
            [5.0, 10.0, 15.0],
        )
