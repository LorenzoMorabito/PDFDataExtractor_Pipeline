from typing import Any

import pandas as pd


SUPPORTED_DELTA_WRITE_MODES = {"overwrite", "append", "append_dedup", "merge"}


def _normalize_columns(df: pd.DataFrame, columns: list[str] | None) -> list[str]:
    if not columns:
        return []
    return [col for col in columns if col in df.columns]


def _deduplicate_incoming(
    df: pd.DataFrame,
    key_columns: list[str],
) -> tuple[pd.DataFrame, dict[str, int]]:
    if not key_columns:
        return df.copy(), {"input_rows": int(len(df)), "duplicate_input_rows": 0}

    deduped = df.drop_duplicates(subset=key_columns, keep="last").reset_index(drop=True)
    return deduped, {
        "input_rows": int(len(df)),
        "duplicate_input_rows": int(len(df) - len(deduped)),
    }


def _align_to_target_columns(
    df: pd.DataFrame,
    target_columns: list[str],
) -> pd.DataFrame:
    extra_columns = [col for col in df.columns if col not in target_columns]
    if extra_columns:
        raise ValueError(
            "Incoming schema has columns not present in target Delta table: "
            + ", ".join(extra_columns)
        )

    aligned = df.copy()
    for col in target_columns:
        if col not in aligned.columns:
            aligned[col] = pd.NA
    return aligned[target_columns]


def _write_new_delta_table(
    spark_df,
    table_name: str,
    *,
    mode: str,
    partition_by: list[str],
) -> None:
    writer = spark_df.write.format("delta").mode(mode)
    if partition_by:
        writer = writer.partitionBy(*partition_by)
    if mode == "overwrite":
        writer = writer.option("overwriteSchema", "true")
    writer.saveAsTable(table_name)


def _merge_condition(key_columns: list[str]) -> str:
    return " AND ".join(f"t.`{col}` <=> s.`{col}`" for col in key_columns)


def prepare_dataframe_for_delta(
    df: pd.DataFrame,
    *,
    column_mapping: dict[str, str] | None = None,
    required_columns: list[str] | None = None,
    default_values: dict[str, Any] | None = None,
    target_columns: list[str] | None = None,
) -> pd.DataFrame:
    prepared = df.rename(columns=column_mapping or {}).copy()

    for column, value in (default_values or {}).items():
        if column not in prepared.columns:
            prepared[column] = value
        else:
            prepared[column] = prepared[column].fillna(value)

    missing_required = [col for col in (required_columns or []) if col not in prepared.columns]
    if missing_required:
        raise ValueError(
            "Incoming dataframe is missing required columns for Delta load: "
            + ", ".join(missing_required)
        )

    if target_columns:
        prepared = _align_to_target_columns(prepared, target_columns)

    return prepared


def controlled_delta_load(
    df: pd.DataFrame,
    table_name: str,
    *,
    write_mode: str,
    key_columns: list[str] | None = None,
    partition_by: list[str] | None = None,
    column_mapping: dict[str, str] | None = None,
    required_columns: list[str] | None = None,
    default_values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from pyspark.sql import SparkSession

    requested_mode = str(write_mode or "overwrite").lower()
    if requested_mode not in SUPPORTED_DELTA_WRITE_MODES:
        raise ValueError(
            "Unsupported Delta write_mode "
            f"{write_mode!r}. Supported values: "
            + ", ".join(sorted(SUPPORTED_DELTA_WRITE_MODES))
            + "."
        )

    prepared_df = prepare_dataframe_for_delta(
        df,
        column_mapping=column_mapping,
        required_columns=required_columns,
        default_values=default_values,
    )

    key_columns = key_columns or (["record_hash"] if "record_hash" in prepared_df.columns else [])
    key_columns = _normalize_columns(prepared_df, key_columns)
    partition_by = _normalize_columns(prepared_df, partition_by)

    deduped_df, audit = _deduplicate_incoming(prepared_df, key_columns)
    audit.update(
        {
            "target_table": table_name,
            "requested_mode": requested_mode,
            "key_columns": list(key_columns),
            "partition_by": list(partition_by),
            "prepared_rows": int(len(deduped_df)),
            "column_mapping": dict(column_mapping or {}),
            "required_columns": list(required_columns or []),
            "default_value_columns": sorted((default_values or {}).keys()),
        }
    )

    spark = SparkSession.builder.getOrCreate()
    table_exists = bool(spark.catalog.tableExists(table_name))
    audit["table_exists_before"] = table_exists

    if not table_exists:
        spark_df = spark.createDataFrame(deduped_df)
        initial_mode = "overwrite" if requested_mode == "overwrite" else "append"
        _write_new_delta_table(
            spark_df,
            table_name,
            mode=initial_mode,
            partition_by=partition_by,
        )
        audit.update(
            {
                "mode_applied": "create",
                "matched_existing_rows": 0,
                "inserted_rows": int(len(deduped_df)),
            }
        )
        return audit

    target_df = spark.table(table_name)
    aligned_df = prepare_dataframe_for_delta(
        deduped_df,
        default_values=default_values,
        required_columns=required_columns,
        target_columns=target_df.columns,
    )
    spark_df = spark.createDataFrame(aligned_df)

    if requested_mode == "overwrite":
        _write_new_delta_table(
            spark_df,
            table_name,
            mode="overwrite",
            partition_by=partition_by,
        )
        audit.update(
            {
                "mode_applied": "overwrite",
                "matched_existing_rows": 0,
                "inserted_rows": int(len(aligned_df)),
            }
        )
        return audit

    if requested_mode == "append":
        spark_df.write.format("delta").mode("append").saveAsTable(table_name)
        audit.update(
            {
                "mode_applied": "append",
                "matched_existing_rows": 0,
                "inserted_rows": int(len(aligned_df)),
            }
        )
        return audit

    if not key_columns:
        raise ValueError(
            f"Delta write_mode {requested_mode!r} requires key_columns. "
            "Define the load key columns explicitly or provide record_hash."
        )

    existing_keys = target_df.select(*key_columns).dropDuplicates()
    source_keys = spark_df.select(*key_columns).dropDuplicates()
    matched_existing_rows = int(source_keys.join(existing_keys, on=key_columns, how="inner").count())

    if requested_mode == "append_dedup":
        rows_to_insert = spark_df.join(existing_keys, on=key_columns, how="left_anti")
        inserted_rows = int(rows_to_insert.count())
        if inserted_rows:
            rows_to_insert.write.format("delta").mode("append").saveAsTable(table_name)
        audit.update(
            {
                "mode_applied": "append_dedup",
                "matched_existing_rows": matched_existing_rows,
                "inserted_rows": inserted_rows,
            }
        )
        return audit

    from delta.tables import DeltaTable

    delta_table = DeltaTable.forName(spark, table_name)
    delta_table.alias("t").merge(
        spark_df.alias("s"),
        _merge_condition(key_columns),
    ).whenNotMatchedInsertAll().execute()

    audit.update(
        {
            "mode_applied": "merge",
            "matched_existing_rows": matched_existing_rows,
            "inserted_rows": int(len(aligned_df) - matched_existing_rows),
        }
    )
    return audit
