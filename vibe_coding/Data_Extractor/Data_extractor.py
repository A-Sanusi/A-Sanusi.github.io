import io
import numpy as np
import pandas as pd
import scipy.stats as stats
import streamlit as st

st.set_page_config(page_title="Ekstrak Data", layout="wide")
st.link_button("Menu", "https://a-sanusi.github.io/vibe_coding/vibe_coding.html")
st.title("Ekstrak Data")


# --- HELPER FUNCTIONS ---
def convert_df_to_excel(df, sheet_name="Sheet1"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=True, sheet_name=sheet_name)
    return output.getvalue()

# --- EXTRACTION FUNCTIONS FOR EACH BUTTON/OPTION ---
def process_database(uploaded_file):
    df_siswa_raw = pd.read_excel(uploaded_file, sheet_name="DATA BASE")
    df_siswa = df_siswa_raw.dropna(how="all").copy()

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
    return df_merged

def process_kehadiran(uploaded_file):
    print(f"Coming Soon")

def process_binsik(uploaded_file):
    print(f"Coming Soon")

# --- NAVIGATION BUTTONS / TABS ---
tab_db, tab_kehadiran, tab_binsik = st.tabs(
    ["🔴 Ekstrak Database", "🔴 Ekstrak Kehadiran (coming soon)", "🔴 Ekstrak Nilai Binsik (coming soon)"]
)

# 1. TAB DATABASE
with tab_db:
    st.header("Ekstrak Database")
    uploaded_db = st.file_uploader(
        "Upload File Excel Database",
        type=["xlsx", "xls", "xlsm"],
        key="uploader_db",
    )
    if uploaded_db is None:
        st.info("Silakan masukkan data Excel")
    if uploaded_db is not None:
        df_result = process_database(uploaded_db)
        st.dataframe(df_result, use_container_width=True)

        excel_bytes = convert_df_to_excel(df_result, sheet_name="Database")
        st.download_button(
            label="Download Database",
            data=excel_bytes,
            file_name="Database.xlsx",
            key="download_db",
        )

# 2. TAB KEHADIRAN
with tab_kehadiran:
    st.info("Coming Soon")

# 3. TAB BINSIK
with tab_binsik:
    st.info("Coming Soon")

