import unittest
from datetime_bucket_manager import DateTimeBucketManager
#import logging
from datetime import datetime

class TestDateTimeBucketManager(unittest.TestCase):

    #logging.basicConfig(
    #    level=logging.DEBUG,
    #    format="[%(levelname)s] %(message)s",
    #    stream=sys.stdout,
    #    force=True  # Overrides any existing handlers (Python 3.8+)
    #)

    @staticmethod
    def __strToDt(dt_str: str) -> datetime:
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")

    def __submit_new_datetime(self, dateTimeMgr: DateTimeBucketManager, new_datetime: datetime, expected_dt: datetime, expected_dt_list: list[datetime]):
        targ_dt = dateTimeMgr.get_target_datetime_bucket_key(new_datetime)
        self.assertEqual(targ_dt, expected_dt)
        self.assertEqual(dateTimeMgr.datetime_buckets, expected_dt_list)

    def __log_datetime_list(self, datetime_list: list[datetime]):
        i = 0
        for dt in datetime_list:
            dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            logging.info(f"{i}: {dt_str}")
            i += 1

    def test_empty_manager_properties_and_consumed_seconds(self):
        datetime_mgr = DateTimeBucketManager(5)

        self.assertEqual(datetime_mgr.bucket_mins, 5)
        self.assertEqual(datetime_mgr.datetime_buckets, [])
        self.assertEqual(datetime_mgr.start_datetime, datetime.max)
        self.assertEqual(datetime_mgr.end_datetime, datetime.min)
        self.assertEqual(datetime_mgr.get_bucket_interval_secs(), 300.0)

        for get_consumed_seconds in (
            datetime_mgr.get_total_secs_consumed,
            datetime_mgr.get_first_bucket_secs_consumed,
            datetime_mgr.get_last_bucket_secs_consumed,
        ):
            with self.subTest(method=get_consumed_seconds.__name__):
                with self.assertRaisesRegex(Exception, "There are no datetime buckets available"):
                    get_consumed_seconds()

    def test_single_bucket_consumed_seconds_and_datetime_bounds(self):
        datetime_mgr = DateTimeBucketManager(5)
        start = self.__strToDt("2025-11-08 14:02:13")
        end = self.__strToDt("2025-11-08 14:03:47")
        bucket = self.__strToDt("2025-11-08 14:02:00")

        self.assertEqual(datetime_mgr.get_target_datetime_bucket_key(start), bucket)
        self.assertEqual(datetime_mgr.get_target_datetime_bucket_key(end), bucket)

        self.assertEqual(datetime_mgr.datetime_buckets, [bucket])
        self.assertEqual(datetime_mgr.start_datetime, start)
        self.assertEqual(datetime_mgr.end_datetime, end)
        self.assertEqual(datetime_mgr.get_total_secs_consumed(), 94.0)
        self.assertEqual(datetime_mgr.get_first_bucket_secs_consumed(), 94.0)
        self.assertEqual(datetime_mgr.get_last_bucket_secs_consumed(), 94.0)


    def test_multiple_bucket_consumed_seconds(self):
        datetime_mgr = DateTimeBucketManager(5)
        start = self.__strToDt("2025-11-08 14:02:30")
        end = self.__strToDt("2025-11-08 14:11:10")
        expected_buckets = [
            self.__strToDt("2025-11-08 14:02:00"),
            self.__strToDt("2025-11-08 14:07:00"),
        ]
        second_bucket_start = self.__strToDt("2025-11-08 14:07:00")

        self.assertEqual(
            datetime_mgr.get_target_datetime_bucket_key(start), expected_buckets[0]
        )
        self.assertEqual(
            datetime_mgr.get_target_datetime_bucket_key(second_bucket_start),
            expected_buckets[1],
        )
        self.assertEqual(
            datetime_mgr.get_target_datetime_bucket_key(end), expected_buckets[1]
        )

        self.assertEqual(datetime_mgr.datetime_buckets, expected_buckets)
        self.assertEqual(datetime_mgr.get_total_secs_consumed(), 520.0)
        self.assertEqual(datetime_mgr.get_first_bucket_secs_consumed(), 270.0)
        self.assertEqual(datetime_mgr.get_last_bucket_secs_consumed(), 250.0)


    def test_datetime_buckets_returns_a_copy(self):
        datetime_mgr = DateTimeBucketManager(5)
        bucket = self.__strToDt("2025-11-08 14:02:00")
        datetime_mgr.get_target_datetime_bucket_key(
            self.__strToDt("2025-11-08 14:02:13")
        )

        returned_buckets = datetime_mgr.datetime_buckets
        returned_buckets.clear()

        self.assertEqual(datetime_mgr.datetime_buckets, [bucket])


    def test_datetime_list(self):
        expected_dt_list: list[datetime] = []
        datetime_mgr = DateTimeBucketManager(5)
        self.assertEqual(datetime_mgr.bucket_mins, 5)

        expected_dt = self.__strToDt("2025-11-08 14:00:00")
        expected_dt_list.append(expected_dt)
        self.__submit_new_datetime(datetime_mgr, self.__strToDt("2025-11-08 14:00:22"), expected_dt, expected_dt_list)

        self.__submit_new_datetime(datetime_mgr, self.__strToDt("2025-11-08 14:01:23"), expected_dt, expected_dt_list)

        expected_dt = self.__strToDt("2025-11-08 13:55:00")
        expected_dt_list.insert(0, expected_dt)
        self.__submit_new_datetime(datetime_mgr, self.__strToDt("2025-11-08 13:59:59"), expected_dt, expected_dt_list)

        self.__submit_new_datetime(datetime_mgr, self.__strToDt("2025-11-08 13:59:01"), expected_dt, expected_dt_list)

        self.__submit_new_datetime(datetime_mgr, self.__strToDt("2025-11-08 13:55:01"), expected_dt, expected_dt_list)

        expected_dt = self.__strToDt("2025-11-08 13:45:00")
        expected_dt_list.insert(0, self.__strToDt("2025-11-08 13:50:00"))
        expected_dt_list.insert(0, expected_dt)
        self.__submit_new_datetime(datetime_mgr, self.__strToDt("2025-11-08 13:49:01"), expected_dt, expected_dt_list)

        expected_dt = self.__strToDt("2025-11-08 14:15:00")
        expected_dt_list.append(self.__strToDt("2025-11-08 14:05:00"))
        expected_dt_list.append(self.__strToDt("2025-11-08 14:10:00"))
        expected_dt_list.append(expected_dt)
        self.__submit_new_datetime(datetime_mgr, self.__strToDt("2025-11-08 14:15:59"), expected_dt, expected_dt_list)

        self.__submit_new_datetime(datetime_mgr, self.__strToDt("2025-11-08 14:19:59"), expected_dt, expected_dt_list)

        self.__submit_new_datetime(datetime_mgr, self.__strToDt("2025-11-08 14:19:01"), expected_dt, expected_dt_list)

        expected_dt = self.__strToDt("2025-11-08 14:20:00")
        expected_dt_list.append(expected_dt)
        self.__submit_new_datetime(datetime_mgr, self.__strToDt("2025-11-08 14:20:01"), expected_dt, expected_dt_list)

        self.__submit_new_datetime(datetime_mgr, self.__strToDt("2025-11-08 14:20:59"), expected_dt, expected_dt_list)

        #self.__log_datetime_list(datetime_mgr.datetime_buckets)

