import statistics

from Sample import RollupSample, Sample
from types import MappingProxyType
from typing import Final, Mapping

OVERALL_SUMMARY_LABEL_PREFIX: Final[str] = "overall_rollup"
BUCKET_SUMMARY_LABEL_PREFIX: Final[str] = "bucket_rollup"


class SampleCollection:
    __slots__ = ("__sample_dict", "__label_list")

    def __init__(self) -> None:
        self.__sample_dict: dict[str, list[Sample] | RollupSample] = {}
        self.__label_list: list[str] = []

    @property
    def sample_dict(self) -> Mapping[str, list[Sample] | RollupSample]:
        return MappingProxyType(self.__sample_dict)

    @property
    def label_list(self) -> list[str]:
        return self.__label_list.copy()

    @staticmethod
    def __get_label_str(prefix1: str | None, prefix2: str | None, label: str) -> str:
        prefixes = (prefix for prefix in (prefix1, prefix2) if prefix and prefix.strip())
        prefix = "_".join(prefixes)
        return f"{prefix}_{label}" if prefix else label

    @classmethod
    def __get_sample_label(cls, prefix: str, label: str) -> str:
        return cls.__get_label_str(prefix, None, label)

    @classmethod
    def __get_overall_rollup_label(cls, label: str) -> str:
        return cls.__get_label_str(OVERALL_SUMMARY_LABEL_PREFIX, None, label)

    @classmethod
    def __get_bucket_rollup_label(cls, prefix: str, label: str) -> str:
        return cls.__get_label_str(prefix, BUCKET_SUMMARY_LABEL_PREFIX, label)

    def add_sample(
        self, prefix: str, label: str, success: bool, elapsed_ms: int
    ) -> None:
        sample = Sample(
            total_count=1,
            elapsed_ms=elapsed_ms,
            success_count=int(success),
            success_elapsed_ms=elapsed_ms if success else 0.0,
        )

        sample_label = self.__get_sample_label(prefix, label)
        self.__sample_dict.setdefault(sample_label, []).append(sample)

        self.__update_rollup_sample(
            self.__get_bucket_rollup_label(prefix, label), sample
        )
        self.__update_rollup_sample(self.__get_overall_rollup_label(label), sample)

        if label not in self.__label_list:
            self.__label_list.append(label)

    def __update_rollup_sample(self, rollup_label: str, sample: Sample) -> None:
        existing = self.__sample_dict.get(rollup_label)
        if existing is None:
            self.__sample_dict[rollup_label] = RollupSample(
                sample.total_count,
                sample.elapsed_ms,
                sample.success_count,
                sample.success_elapsed_ms,
            )
        else:
            if not isinstance(existing, RollupSample):
                raise TypeError(f"{rollup_label!r} is not a rollup sample")
            self.__sample_dict[rollup_label] = RollupSample.combine_samples(sample, existing)

    @classmethod
    def __update_percentile_elapsed_ms(
        cls, rollup_sample: RollupSample, elapsed_ms_values: list[float]
    ) -> None:
        if not elapsed_ms_values:
            return
        cuts = statistics.quantiles(elapsed_ms_values, n=100, method="exclusive")
        rollup_sample.set_elapsed_ms_percentile(cuts[49], cuts[74], cuts[89], cuts[94])

    def generate_rollup_metrics(
        self,
        prefix_list: list[str],
        first_bucket_consumed_secs: float,
        last_bucket_consumed_secs: float,
        standard_bucket_secs: float,
        total_consumed_secs: float,
    ) -> None:
        last_bucket_index = len(prefix_list) - 1

        for label in self.__label_list:
            elapsed_ms_overall: list[float] = []

            for index, prefix in enumerate(prefix_list):
                if index == last_bucket_index:
                    consumed_secs = last_bucket_consumed_secs
                elif index == 0:
                    consumed_secs = first_bucket_consumed_secs
                else:
                    consumed_secs = standard_bucket_secs

                samples = self.__sample_dict.get(self.__get_sample_label(prefix, label))
                if not isinstance(samples, list):
                    continue

                elapsed_ms_bucket = [sample.elapsed_ms for sample in samples]
                elapsed_ms_overall.extend(elapsed_ms_bucket)

                rollup_sample = self.__sample_dict.get(
                    self.__get_bucket_rollup_label(prefix, label)
                )
                if isinstance(rollup_sample, RollupSample):
                    rollup_sample.set_consumed_secs(consumed_secs)
                    self.__update_percentile_elapsed_ms(
                        rollup_sample, elapsed_ms_bucket
                    )

            if elapsed_ms_overall:
                overall_rollup = self.__sample_dict.get(
                    self.__get_overall_rollup_label(label)
                )
                if isinstance(overall_rollup, RollupSample):
                    overall_rollup.set_consumed_secs(total_consumed_secs)
                    self.__update_percentile_elapsed_ms(
                        overall_rollup, elapsed_ms_overall
                    )

    def get_overall_rollup_sample(self, label: str) -> RollupSample:
        rollup_sample = self.__sample_dict[self.__get_overall_rollup_label(label)]
        if not isinstance(rollup_sample, RollupSample):
            raise TypeError(f"Overall sample for {label!r} is not a rollup")
        return rollup_sample

    def get_bucket_stats(
        self, prefix_list: list[str], label: str
    ) -> tuple[list[int], list[float], list[float]]:
        total_counts: list[int] = []
        average_elapsed_ms: list[float] = []
        items_per_second: list[float] = []

        for prefix in prefix_list:
            rollup_sample = self.__sample_dict.get(
                self.__get_bucket_rollup_label(prefix, label)
            )
            if isinstance(rollup_sample, RollupSample):
                total_counts.append(rollup_sample.total_count)
                average_elapsed_ms.append(rollup_sample.calc_avg_elapsed_ms())
                items_per_second.append(rollup_sample.calc_items_per_second())
            else:
                total_counts.append(0)
                average_elapsed_ms.append(0.0)
                items_per_second.append(0.0)

        return total_counts, average_elapsed_ms, items_per_second
