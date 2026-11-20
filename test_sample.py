import unittest

from sample import RollupSample, Sample


class TestSample(unittest.TestCase):
    def test_sample_properties(self):
        sample = Sample(4, 100, 3, 75)

        self.assertEqual(sample.total_count, 4)
        self.assertEqual(sample.elapsed_ms, 100.0)
        self.assertEqual(sample.success_count, 3)
        self.assertEqual(sample.success_elapsed_ms, 75.0)
        self.assertEqual(sample.error_count, 1)

    def test_rollup_calculations_and_percentiles(self):
        sample = RollupSample(
            total_count=4,
            elapsed_ms=100,
            min_ms=10,
            max_ms=40,
            success_count=3,
            success_elapsed_ms=75,
        )

        self.assertEqual(sample.consumed_secs, 0.0)
        self.assertEqual(sample.min_ms, 10)
        self.assertEqual(sample.max_ms, 40)
        self.assertEqual(sample.calc_avg_elapsed_ms(), 25.0)
        self.assertEqual(sample.calc_error_rate(), 25.0)
        self.assertEqual(sample.calc_items_per_second(), 0.0)

        sample.set_consumed_secs(10)
        sample.set_elapsed_ms_percentile(12.5, 20.0, 30.0, 40.0)

        self.assertEqual(sample.consumed_secs, 10.0)
        self.assertEqual(sample.calc_items_per_second(), 0.4)
        self.assertEqual(sample.perc_50, 12.5)
        self.assertEqual(sample.perc_75, 20.0)
        self.assertEqual(sample.perc_90, 30.0)
        self.assertEqual(sample.perc_95, 40.0)

    def test_error_rate_with_all_errors_or_no_errors(self):
        no_successes = RollupSample(
            total_count=2,
            elapsed_ms=10,
            min_ms=4,
            max_ms=6,
            success_count=0,
            success_elapsed_ms=0,
        )
        self.assertEqual(no_successes.calc_error_rate(), 100.0)

        no_errors = RollupSample(
            total_count=2,
            elapsed_ms=10,
            min_ms=4,
            max_ms=6,
            success_count=2,
            success_elapsed_ms=10,
        )
        self.assertEqual(no_errors.calc_error_rate(), 0.0)

    def test_combine_sample_into_rollup(self):
        sample = Sample(1, 5, 1, 5)
        rollup = RollupSample(
            total_count=3,
            elapsed_ms=20,
            min_ms=7,
            max_ms=10,
            success_count=2,
            success_elapsed_ms=10,
        )

        combined = RollupSample.combine_samples(sample, rollup)

        self.assertIsInstance(combined, RollupSample)
        self.assertEqual(combined.total_count, 4)
        self.assertEqual(combined.elapsed_ms, 25.0)
        self.assertEqual(combined.min_ms, 5.0)
        self.assertEqual(combined.max_ms, 10)
        self.assertEqual(combined.success_count, 3)
        self.assertEqual(combined.success_elapsed_ms, 15.0)
        self.assertEqual(combined.error_count, 1)
        self.assertEqual(combined.consumed_secs, 0.0)
        self.assertEqual(combined.perc_50, 0.0)

    def test_combine_sample_updates_minimum_and_maximum(self):
        rollup = RollupSample(
            total_count=2,
            elapsed_ms=20,
            min_ms=8,
            max_ms=12,
            success_count=2,
            success_elapsed_ms=20,
        )

        lower_sample = RollupSample.combine_samples(Sample(1, 5, 1, 5), rollup)
        higher_sample = RollupSample.combine_samples(Sample(1, 15, 1, 15), rollup)

        self.assertEqual((lower_sample.min_ms, lower_sample.max_ms), (5.0, 12))
        self.assertEqual((higher_sample.min_ms, higher_sample.max_ms), (8, 15.0))

    def test_rollup_setters_can_only_be_used_once(self):
        sample = RollupSample(
            total_count=1,
            elapsed_ms=5,
            min_ms=5,
            max_ms=5,
            success_count=1,
            success_elapsed_ms=5,
        )
        sample.set_consumed_secs(1.5)
        sample.set_elapsed_ms_percentile(1.0, 2.0, 3.0, 4.0)

        with self.assertRaisesRegex(Exception, "consumed_secs is already set"):
            sample.set_consumed_secs(2)
        with self.assertRaisesRegex(Exception, "elapsed ms percentiles are already set"):
            sample.set_elapsed_ms_percentile(2.0, 3.0, 4.0, 5.0)

    def test_consumed_seconds_must_be_numeric(self):
        sample = RollupSample(
            total_count=1,
            elapsed_ms=5,
            min_ms=5,
            max_ms=5,
            success_count=1,
            success_elapsed_ms=5,
        )

        with self.assertRaisesRegex(TypeError, "secs must be a number"):
            sample.set_consumed_secs("1")
