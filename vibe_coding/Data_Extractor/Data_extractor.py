import io
import numpy as np
import pandas as pd
import scipy.stats as stats
import streamlit as st

st.set_page_config(page_title="Ekstrak Data")
st.link_button("Menu", "https://a-sanusi.github.io/vibe_coding/vibe_coding.html")
st.title("Ekstrak Data")

uploaded_file = st.file_uploader(
    "Upload File Excel Database", type=["xlsx", "xls", "xlsm"]
)

if uploaded_file is None:
    st.info("Silakan upload file excel untuk melanjutkan.")
    st.stop()

# Upload Excel File
excel_file = pd.ExcelFile(uploaded_file)
df_siswa_raw = pd.read_excel(uploaded_file, sheet_name="DATA BASE")
df_siswa = df_siswa_raw.dropna(how="all").copy()

# Kolom
selected_columns = [
    "NAMA SISWA",
    "NAMA AKUN TO",
    "ASAL SEKOLAH",
    "JURUSAN",
    "PROGRAM BELAJAR",
    "KELAS (DI PRIORITY)",
    "MINAT PTN",
    "MINAT SEKOLAH KEDINASAN",
]

df_merged = df_siswa[selected_columns]
df_merged.index = range(1, len(df_merged) + 1)
df_merged = df_merged.astype(object).fillna("-")
st.dataframe(df_merged)

# Export Excel
def convert_df_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=True, sheet_name="Database")
    return output.getvalue()
excel_bytes = convert_df_to_excel(df_merged)
st.dataframe(df_merged, use_container_width=True)

st.download_button(
    label="Download Database",
    data=excel_bytes,
    file_name="Database.xlsx",
)
