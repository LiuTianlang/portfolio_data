from __future__ import annotations

import pandas as pd
import streamlit as st

from csv_picker import load_csv_from_picker
from filters import render_filters
from visualization import render_chart_builder


st.set_page_config(page_title="CSV Insight Studio", layout="wide")

st.title("CSV Insight Studio")
st.caption("Upload a CSV, filter rows, and explore charts with flexible aggregation.")

data = load_csv_from_picker("Upload CSV")

if data is None:
    st.info("Upload a CSV file to begin.")
    st.stop()

if data.empty:
    st.warning("The uploaded CSV has no rows.")
    st.stop()

filtered_data = render_filters(data)

st.markdown("---")

numeric_columns = [
    col for col in filtered_data.columns if pd.api.types.is_numeric_dtype(filtered_data[col])
]

if not numeric_columns:
    st.warning("No numeric columns found for charting.")
    st.stop()

render_chart_builder(filtered_data, list(filtered_data.columns), numeric_columns)

st.markdown("---")
st.subheader("3) Preview filtered data")
st.dataframe(filtered_data, use_container_width=True)
