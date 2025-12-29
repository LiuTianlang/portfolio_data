from __future__ import annotations

import io

import pandas as pd
import streamlit as st
import yaml


def _load_yaml_config(
    yaml_bytes: bytes,
    container: st.delta_generator.DeltaGenerator,
) -> dict | None:
    try:
        yaml_data = yaml.safe_load(yaml_bytes)
    except yaml.YAMLError as exc:
        container.error(f"Unable to parse the YAML file: {exc}")
        return None

    if not isinstance(yaml_data, dict):
        container.error("YAML config must be a mapping with version metadata and configs.")
        return None

    config_names = [
        key for key in yaml_data.keys() if key not in {"version", "filter_types"}
    ]
    if not config_names:
        container.error("YAML config is missing a dataset definition.")
        return None

    if len(config_names) == 1:
        config_name = config_names[0]
    else:
        config_name = container.selectbox("Select YAML config", options=config_names)

    config = yaml_data.get(config_name)
    if not isinstance(config, dict):
        container.error("Selected YAML config must be a mapping of settings.")
        return None

    return config


def _apply_yaml_settings(df: pd.DataFrame, config: dict, container: st.delta_generator.DeltaGenerator) -> pd.DataFrame | None:
    required_columns = config.get("required_columns") or []
    if not isinstance(required_columns, list):
        container.error("required_columns must be a list of column names.")
        return None

    missing = [name for name in required_columns if name not in df.columns]
    if missing:
        container.error(f"Missing required columns: {', '.join(missing)}")
        return None

    column_specs = config.get("columns") or {}
    if not isinstance(column_specs, dict):
        container.error("columns must be a mapping of column definitions.")
        return None

    for column_name, column_config in column_specs.items():
        if column_name not in df.columns or not isinstance(column_config, dict):
            continue
        dtype = column_config.get("type")
        fmt = column_config.get("format")

        if dtype == "datetime":
            df[column_name] = pd.to_datetime(df[column_name], format=fmt, errors="coerce")
        elif dtype == "int":
            df[column_name] = pd.to_numeric(df[column_name], errors="coerce").astype("Int64")
        elif dtype == "float":
            df[column_name] = pd.to_numeric(df[column_name], errors="coerce")
        elif dtype == "string":
            df[column_name] = df[column_name].astype("string")
        elif dtype == "category":
            df[column_name] = df[column_name].astype("category")
        elif dtype == "bool":
            df[column_name] = df[column_name].astype("boolean")

    fillna = config.get("fillna")
    if isinstance(fillna, dict):
        df = df.fillna(fillna)

    return df


def load_csv_from_picker(
    label: str = "Upload CSV",
    container: st.delta_generator.DeltaGenerator | None = None,
) -> pd.DataFrame | None:
    """Render file pickers and return a DataFrame when a file is selected."""
    target = container or st

    uploaded_file = target.file_uploader(label, type=["csv"])
    yaml_file = target.file_uploader("Upload YAML config (optional)", type=["yml", "yaml"])

    if not uploaded_file:
        return None

    yaml_config = None
    if yaml_file:
        yaml_config = _load_yaml_config(yaml_file.getvalue(), target)
        if yaml_config is None:
            return None

    read_kwargs: dict[str, str] = {}
    if yaml_config:
        if yaml_config.get("encoding"):
            read_kwargs["encoding"] = str(yaml_config["encoding"])
        if yaml_config.get("sep"):
            read_kwargs["sep"] = str(yaml_config["sep"])

    try:
        df = pd.read_csv(io.BytesIO(uploaded_file.getvalue()), **read_kwargs)
    except Exception as exc:  # noqa: BLE001 - surface file errors to the user
        target.error(f"Unable to read the CSV file: {exc}")
        return None

    if yaml_config:
        df = _apply_yaml_settings(df, yaml_config, target)
        if df is None:
            return None

    return df
