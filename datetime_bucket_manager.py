from datetime import datetime, timedelta

######################################
##  CLASS DATE TIME BUCKET MANAGER  ##
######################################

class DateTimeBucketManager:
    __slots__ = (
        "__bucket_mins",
        "__datetime_buckets",
        "__start_datetime",
        "__end_datetime",
    )

    def __init__(self, bucket_mins: int) -> None:
        if bucket_mins <= 0:
            raise ValueError("bucket_mins must be greater than zero")

        self.__bucket_mins = bucket_mins
        self.__datetime_buckets: list[datetime] = []
        self.__start_datetime = datetime.max
        self.__end_datetime = datetime.min

    @property
    def bucket_mins(self) -> int:
        return self.__bucket_mins

    @property
    def datetime_buckets(self) -> list[datetime]:
        return self.__datetime_buckets.copy()

    @property
    def start_datetime(self) -> datetime:
        return self.__start_datetime

    @property
    def end_datetime(self) -> datetime:
        return self.__end_datetime

    def get_total_secs_consumed(self) -> float:
        self.__ensure_buckets_available()
        return (self.__end_datetime - self.__start_datetime).total_seconds()

    def get_first_bucket_secs_consumed(self) -> float:
        self.__ensure_buckets_available()
        if len(self.__datetime_buckets) == 1:
            return self.get_total_secs_consumed()

        unused_secs = (self.__start_datetime - self.__datetime_buckets[0]).total_seconds()
        return self.get_bucket_interval_secs() - unused_secs

    def get_last_bucket_secs_consumed(self) -> float:
        self.__ensure_buckets_available()
        if len(self.__datetime_buckets) == 1:
            return self.get_total_secs_consumed()

        return (self.__end_datetime - self.__datetime_buckets[-1]).total_seconds()

    def get_bucket_interval_secs(self) -> float:
        return self.__bucket_mins * 60.0

    def __ensure_buckets_available(self) -> None:
        if not self.__datetime_buckets:
            raise Exception("There are no datetime buckets available")

    def __extend_buckets_to_include(self, new_datetime: datetime) -> None:
        interval = timedelta(minutes=self.__bucket_mins)
        while new_datetime < self.__datetime_buckets[0]:
            self.__datetime_buckets.insert(0, self.__datetime_buckets[0] - interval)

        while new_datetime >= self.__datetime_buckets[-1] + interval:
            self.__datetime_buckets.append(self.__datetime_buckets[-1] + interval)

    def get_target_datetime_bucket_key(self, new_datetime: datetime) -> datetime:
        self.__start_datetime = min(self.__start_datetime, new_datetime)
        self.__end_datetime = max(self.__end_datetime, new_datetime)

        if not self.__datetime_buckets:
            first_bucket = new_datetime.replace(second=0, microsecond=0)
            self.__datetime_buckets.append(first_bucket)
        else:
            self.__extend_buckets_to_include(new_datetime)

        elapsed = new_datetime - self.__datetime_buckets[0]
        bucket_index = int(elapsed // timedelta(minutes=self.__bucket_mins))
        return self.__datetime_buckets[bucket_index]
