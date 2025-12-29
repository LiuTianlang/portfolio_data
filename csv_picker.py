import io

import pandas as pd
import streamlit as st


def load_csv_from_picker(label: str = "Upload CSV") -> pd.DataFrame | None:
    """Render a file picker and return a DataFrame when a file is selected."""
    uploaded_file = st.file_uploader(label, type=["csv"])
    if not uploaded_file:
        return None

    try:
        return pd.read_csv(io.BytesIO(uploaded_file.getvalue()))
    except Exception as exc:  # noqa: BLE001 - surface file errors to the user
        st.error(f"Unable to read the CSV file: {exc}")
        return None
