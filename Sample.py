
####################
##  CLASS SAMPLE  ##
####################

class Sample:
    __slots__ = (
        "__total_count",
        "__elapsed_ms",
        "__success_count",
        "__success_elapsed_ms",
    )

    def __init__(
        self,
        total_count: int,
        elapsed_ms: float,
        success_count: int,
        success_elapsed_ms: float,
    ) -> None:
        self.__total_count = total_count
        self.__success_count = success_count
        self.__elapsed_ms = float(elapsed_ms)
        self.__success_elapsed_ms = float(success_elapsed_ms)

    @property
    def total_count(self) -> int:
        return self.__total_count

    @property
    def success_count(self) -> int:
        return self.__success_count

    @property
    def error_count(self) -> int:
        return self.__total_count - self.__success_count

    @property
    def elapsed_ms(self) -> float:
        return self.__elapsed_ms

    @property
    def success_elapsed_ms(self) -> float:
        return self.__success_elapsed_ms


#############################################
##  CLASS ROLLUP SAMPLE (Child of Sample)  ##
#############################################

class RollupSample(Sample):
    __slots__ = (
        "__consumed_secs",
        "__elapsed_ms_percentiles_set",
        "__consumed_secs_set",
        "__min_ms",
        "__max_ms",
        "__perc_50",
        "__perc_75",
        "__perc_90",
        "__perc_95",
    )

    def __init__(
        self,
        total_count: int,
        elapsed_ms: float,
        min_ms: float,
        max_ms: float,
        success_count: int,
        success_elapsed_ms: float,
    ) -> None:
        super().__init__(total_count, elapsed_ms, success_count, success_elapsed_ms)
        self.__consumed_secs = 0.0
        self.__min_ms = min_ms
        self.__max_ms = max_ms
        self.__perc_50 = 0.0
        self.__perc_75 = 0.0
        self.__perc_90 = 0.0
        self.__perc_95 = 0.0
        self.__consumed_secs_set = False
        self.__elapsed_ms_percentiles_set = False

    @property
    def consumed_secs(self) -> float:
        return self.__consumed_secs

    @property
    def min_ms(self) -> float:
        return self.__min_ms

    @property
    def max_ms(self) -> float:
        return self.__max_ms

    @property
    def perc_50(self) -> float:
        return self.__perc_50

    @property
    def perc_75(self) -> float:
        return self.__perc_75

    @property
    def perc_90(self) -> float:
        return self.__perc_90

    @property
    def perc_95(self) -> float:
        return self.__perc_95

    def set_consumed_secs(self, secs: float) -> None:
        if self.__consumed_secs_set:
            raise Exception("consumed_secs is already set")
        if not isinstance(secs, (int, float)):
            raise TypeError(f"secs must be a number, got {type(secs).__name__}: {secs!r}")

        self.__consumed_secs = float(secs)
        self.__consumed_secs_set = True

    def set_elapsed_ms_percentile(
        self, perc_50: float, perc_75: float, perc_90: float, perc_95: float
    ) -> None:
        if self.__elapsed_ms_percentiles_set:
            raise Exception("elapsed ms percentiles are already set")

        self.__perc_50 = perc_50
        self.__perc_75 = perc_75
        self.__perc_90 = perc_90
        self.__perc_95 = perc_95
        self.__elapsed_ms_percentiles_set = True

    def calc_avg_elapsed_ms(self) -> float:
        return self.elapsed_ms / self.total_count

    def calc_error_rate(self) -> float:
        return self.error_count / self.total_count * 100

    def calc_items_per_second(self) -> float:
        if self.__consumed_secs == 0.0:
            return 0.0
        return self.total_count / self.__consumed_secs

    @staticmethod
    def combine_samples(sample: Sample, rollup_sample: RollupSample) -> RollupSample:
        return RollupSample(
            total_count=sample.total_count + rollup_sample.total_count,
            elapsed_ms=sample.elapsed_ms + rollup_sample.elapsed_ms,
            min_ms=sample.elapsed_ms if sample.elapsed_ms < rollup_sample.min_ms else rollup_sample.min_ms,
            max_ms=sample.elapsed_ms if sample.elapsed_ms > rollup_sample.max_ms else rollup_sample.max_ms,
            success_count=sample.success_count + rollup_sample.success_count,
            success_elapsed_ms=(sample.success_elapsed_ms + rollup_sample.success_elapsed_ms)
        )
