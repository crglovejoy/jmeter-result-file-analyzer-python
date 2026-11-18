import argparse
import csv
import os
import sys
import traceback
import tomllib

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence

from DateTimeBucketManager import DateTimeBucketManager
from SampleCollection import SampleCollection

LABEL_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
OUTPUT_DATETIME_FORMAT = "%Y-%m-%d %H:%M"
REQUIRED_HEADERS = {"timeStamp", "elapsed", "label", "success"}


@dataclass
class HeaderIndexes:
    time_col: int = -1
    elapsed_col: int = -1
    success_col: int = -1
    label_col: int = -1

    def check_indexes_set(self) -> bool:
        return min(
            self.time_col,
            self.elapsed_col,
            self.success_col,
            self.label_col,
        ) >= 0


def str_to_bool(value: str) -> bool:
    return value.strip().lower() in {"true", "yes", "y", "1", "t"}


def label_datetime_format_string() -> str:
    return LABEL_DATETIME_FORMAT


def output_datetime_format_string() -> str:
    return OUTPUT_DATETIME_FORMAT


def get_datetime_str_list(
    datetime_list: list[datetime], format_string: str
) -> list[str]:
    return [value.strftime(format_string) for value in datetime_list]


def _find_header_indexes(headers: Sequence[str]) -> HeaderIndexes | None:
    positions = {header: index for index, header in enumerate(headers)}
    if not REQUIRED_HEADERS.issubset(positions):
        return None

    return HeaderIndexes(
        time_col=positions["timeStamp"],
        elapsed_col=positions["elapsed"],
        success_col=positions["success"],
        label_col=positions["label"],
    )


def find_headers(line: str) -> HeaderIndexes | None:
    headers = next(csv.reader([line]), [])
    return _find_header_indexes(headers)


def _generate_metrics(
    fields: Sequence[str],
    header_indexes: HeaderIndexes,
    datetime_bucket_manager: DateTimeBucketManager,
    sample_collection: SampleCollection,
) -> None:
    required_field_count = max(
        header_indexes.time_col,
        header_indexes.elapsed_col,
        header_indexes.success_col,
        header_indexes.label_col,
    ) + 1
    if len(fields) < required_field_count:
        raise ValueError(
            f"expected at least {required_field_count} columns, got {len(fields)}"
        )

    sample_datetime = datetime.fromtimestamp(
        int(fields[header_indexes.time_col].strip()) / 1000
    )
    bucket = datetime_bucket_manager.get_target_datetime_bucket_key(sample_datetime)
    sample_collection.add_sample(
        bucket.strftime(LABEL_DATETIME_FORMAT),
        fields[header_indexes.label_col].strip(),
        str_to_bool(fields[header_indexes.success_col]),
        int(fields[header_indexes.elapsed_col].strip())
    )


def generate_metrics(
    line: str,
    header_indexes: HeaderIndexes,
    datetime_bucket_manager: DateTimeBucketManager,
    sample_collection: SampleCollection,
) -> None:
    if not line.strip():
        return

    fields = next(csv.reader([line]), [])
    _generate_metrics(
        fields, header_indexes, datetime_bucket_manager, sample_collection
    )


def process_file(
    file_path: str | os.PathLike[str],
    datetime_bucket_manager: DateTimeBucketManager,
    sample_collection: SampleCollection
) -> None:
    header_indexes = None

    with open(file_path, "r", encoding="utf-8", newline="") as input_file:
        reader = csv.reader(input_file)
        for row in reader:
            if not row or not any(field.strip() for field in row):
                continue

            if header_indexes is None:
                header_indexes = _find_header_indexes(row)
                continue

            try:
                _generate_metrics(
                    row,
                    header_indexes,
                    datetime_bucket_manager,
                    sample_collection,
                )
            except (IndexError, ValueError) as error:
                raise ValueError(
                    f"Invalid data on CSV line {reader.line_num}: {error}"
                ) from error

    if header_indexes is None:
        raise ValueError("Could not find the required headers in the input file")


def get_overall_stats_list(
    label_list: list[str], sample_collection: SampleCollection
) -> list[str]:
    lines = [
        "OVERALL STATS:\n"
        "label,tot_count,succ_count,err_count,succ_%,requests_per_sec,"
        "avg_succ_elapsed_ms,avg_err_elapsed_ms,avg_elapsed_ms,"
        "50th_%_elapsed_ms,75th_%_elapsed_ms,90th_%_elapsed_ms,95th_%_elapsed_ms\n"
    ]

    for label in label_list:
        rollup_sample = sample_collection.get_overall_rollup_sample(label)
        lines.append(
            f"{label},{rollup_sample.total_count},{rollup_sample.success_count},"
            f"{rollup_sample.error_count},{rollup_sample.calc_success_rate():.2f},"
            f"{rollup_sample.calc_items_per_second():.2f},"
            f"{rollup_sample.calc_avg_success_elapsed_ms():.2f},"
            f"{rollup_sample.calc_avg_error_elapsed_ms():.2f},"
            f"{rollup_sample.calc_avg_elapsed_ms():.2f}, "
            f"{rollup_sample.perc_50:.2f},{rollup_sample.perc_75:.2f},"
            f"{rollup_sample.perc_90:.2f},{rollup_sample.perc_95:.2f}\n"
        )

    lines.append("\n\n")
    return lines


def get_bucket_stats_lists(
    datetime_strings: list[str],
    output_datetime_strings: list[str],
    label_list: list[str],
    sample_collection: SampleCollection
) -> tuple[list[str], list[str], list[str]]:
    headers = ",".join(output_datetime_strings)
    total_count_lines = [f"TOTAL_REQUESTS:\nlabel,{headers}\n"]
    average_lines = [f"AVG ELAPSED MS:\nlabel,{headers}\n"]
    requests_per_second_lines = [f"REQUESTS_PER_SECOND:\nlabel,{headers}\n"]

    for label in label_list:
        total_counts, average_elapsed_ms, requests_per_second = (
            sample_collection.get_bucket_stats(datetime_strings, label)
        )
        total_count_lines.append(
            f"{label},{','.join(str(value) for value in total_counts)}\n"
        )
        average_lines.append(
            f"{label},{','.join(f'{value:.2f}' for value in average_elapsed_ms)}\n"
        )
        requests_per_second_lines.append(
            f"{label},{','.join(f'{value:.2f}' for value in requests_per_second)}\n"
        )

    for lines in (
        total_count_lines,
        average_lines,
        requests_per_second_lines,
    ):
        lines.append("\n\n")

    return total_count_lines, average_lines, requests_per_second_lines


def create_report(
    file_path: str | os.PathLike[str],
    datetime_bucket_manager: DateTimeBucketManager,
    sample_collection: SampleCollection
) -> None:
    labels = sample_collection.label_list
    buckets = datetime_bucket_manager.datetime_buckets
    datetime_strings = get_datetime_str_list(buckets, LABEL_DATETIME_FORMAT)
    output_datetime_strings = get_datetime_str_list(
        buckets, OUTPUT_DATETIME_FORMAT
    )

    sample_collection.generate_rollup_metrics(
        datetime_strings,
        datetime_bucket_manager.get_first_bucket_secs_consumed(),
        datetime_bucket_manager.get_last_bucket_secs_consumed(),
        datetime_bucket_manager.get_bucket_interval_secs(),
        datetime_bucket_manager.get_total_secs_consumed(),
    )

    with open(file_path, "w", encoding="utf-8") as output_file:
        output_file.writelines(get_overall_stats_list(labels, sample_collection))
        total_count_lines, average_lines, requests_per_second_lines = (
            get_bucket_stats_lists(
                datetime_strings,
                output_datetime_strings,
                labels,
                sample_collection,
            )
        )
        output_file.writelines(total_count_lines)
        output_file.writelines(average_lines)
        output_file.writelines(requests_per_second_lines)


def main(config_file: str | os.PathLike[str] = "config.toml") -> None:
    try:
        working_directory = Path.cwd()
        with open(working_directory / config_file, "rb") as f:
            config = tomllib.load(f)
        datetime_bucket_manager = DateTimeBucketManager(config["bucket_minutes"])
        sample_collection = SampleCollection()

        rslt_files = config["jmeter_stats_files"].split("|")
        for file_name in rslt_files:
            process_file(
                working_directory / file_name,
                datetime_bucket_manager,
                sample_collection
            )

        create_report(
            working_directory / config["output_summary_file"],
            datetime_bucket_manager,
            sample_collection
        )

        sys.exit(0)
    except Exception as error:
        print("Exception occurred:", error)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "config_file",
        nargs="?",
        default="config.toml",
        help="TOML configuration file (default: config.toml)",
    )
    main(parser.parse_args().config_file)
