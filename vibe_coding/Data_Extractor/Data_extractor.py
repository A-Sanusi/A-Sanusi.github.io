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

# --- EXTRACTION FUNCTIONS ---
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

# --- NAVIGATION TABS ---
tab_db, tab_to, tab_kehadiran, tab_binsik = st.tabs(
    [
        "🔴 Ekstrak Database",
        "🟣 Ekstrak Nilai TO TKA",
        "🔴 Ekstrak Absensi (coming soon)"
        "🟣 Ekstrak Nilai Binsik (coming soon)",
    ]
)

# ==========================================
# 1. TAB DATABASE
# ==========================================
with tab_db:
    st.header("Ekstrak Database")
    uploaded_db = st.file_uploader(
        "Upload File Excel Database",
        type=["xlsx", "xls", "xlsm"],
        key="uploader_db",
    )

    if uploaded_db is None:
        st.info("Silakan upload file Excel Database untuk melanjutkan.")
    else:
        df_result = process_database(uploaded_db)
        st.dataframe(df_result, use_container_width=True)

        excel_bytes = convert_df_to_excel(df_result, sheet_name="Database")
        st.download_button(
            label="Download Database",
            data=excel_bytes,
            file_name="Database.xlsx",
            key="download_db",
        )

# ==========================================
# 2. TAB NILAI TRY OUT
# ==========================================
with tab_to:
    st.header("Nilai TO kini ada Ekstraknya 🟣")

    col1, col2 = st.columns(2)
    with col1:
        uploaded_siswa = st.file_uploader(
            "Upload File Excel Nama Siswa",
            type=["xlsx", "xls", "xlsm"],
            key="uploader_to_siswa",
        )
    with col2:
        uploaded_to = st.file_uploader(
            "Upload File Try Out",
            type=["xlsx", "xls", "xlsm"],
            key="uploader_to_data",
        )

    if uploaded_siswa is None or uploaded_to is None:
        st.info("Silakan upload kedua file Excel untuk melanjutkan.")
    else:
        # 1. Baca data siswa
        excel_siswa = pd.ExcelFile(uploaded_siswa)
        selected_sheet_siswa = st.selectbox(
            "Pilih Sheet Nama Siswa:",
            excel_siswa.sheet_names,
            key="sheet_siswa_select",
        )

        df_siswa_raw = pd.read_excel(
            uploaded_siswa, sheet_name=selected_sheet_siswa, header=0
        )
        df_siswa = df_siswa_raw.dropna(how="all").copy()

        nama_siswa_col = df_siswa.columns[1]
        nama_akun_col = df_siswa.columns[2]
        df_siswa["key_match"] = (
            df_siswa[nama_akun_col].astype(str).str.strip().str.lower()
        )

        # 2. Proses pengambil nilai dari 3 sheet pilihan
        excel_to = pd.ExcelFile(uploaded_to)

        st.write("### Pilih Sheet Subtes Try Out")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            selected_sheet_1 = st.selectbox(
                "Pilih Sheet Subtes 1:",
                excel_to.sheet_names,
                key="sheet_to_1",
            )
        with col_s2:
            selected_sheet_2 = st.selectbox(
                "Pilih Sheet Subtes 2:",
                excel_to.sheet_names,
                key="sheet_to_2",
            )
        with col_s3:
            selected_sheet_3 = st.selectbox(
                "Pilih Sheet Subtes 3:",
                excel_to.sheet_names,
                key="sheet_to_3",
            )

        target_sheets = [selected_sheet_1, selected_sheet_2, selected_sheet_3]
        df_hasil = df_siswa[
            [nama_siswa_col, nama_akun_col, "key_match"]
        ].copy()

        for sheet in target_sheets:
            if sheet in excel_to.sheet_names:
                df_nilai_raw = pd.read_excel(
                    uploaded_to, sheet_name=sheet, header=7
                ).dropna(how="all")

                nama_akun_2_col = df_nilai_raw.columns[1]
                Total_Benar_TO_col = df_nilai_raw.columns[3]
                nilai_TO_col = df_nilai_raw.columns[4]
                kategori_TO_col = df_nilai_raw.columns[5]

                df_nilai_raw["key_match"] = (
                    df_nilai_raw[nama_akun_2_col]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                )

                df_sub = df_nilai_raw[["key_match", nilai_TO_col]].drop_duplicates(
                    subset=["key_match"]
                )
                df_sub = df_sub.rename(columns={nilai_TO_col: f"Nilai_{sheet}"})

                df_sub_2 = df_nilai_raw[
                    ["key_match", kategori_TO_col]
                ].drop_duplicates(subset=["key_match"])
                df_sub_2 = df_sub_2.rename(
                    columns={kategori_TO_col: f"Kategori_{sheet}"}
                )

                df_sub_3 = df_nilai_raw[
                    ["key_match", Total_Benar_TO_col]
                ].drop_duplicates(subset=["key_match"]).copy()
                df_sub_3[Total_Benar_TO_col] = (
                    pd.to_numeric(df_sub_3[Total_Benar_TO_col], errors="coerce")
                    .round()
                    .astype("Int64")
                )
                df_sub_3 = df_sub_3.rename(
                    columns={Total_Benar_TO_col: f"Jumlah_Nilai_Benar_{sheet}"}
                )

                df_hasil = pd.merge(
                    df_hasil, df_sub_3, on="key_match", how="left"
                )
                df_hasil = pd.merge(df_hasil, df_sub, on="key_match", how="left")
                df_hasil = pd.merge(
                    df_hasil, df_sub_2, on="key_match", how="left"
                )

        df_hasil = df_hasil.drop(columns=["key_match"]).dropna(
            subset=[nama_siswa_col]
        )
        df_hasil = df_hasil.astype(object).fillna("-")
        df_hasil.index = range(1, len(df_hasil) + 1)

        # 3. Tampilkan Hasil & Download
        st.subheader("Tabel Nilai Siswa")
        st.dataframe(df_hasil, use_container_width=True)

        excel_bytes_to = convert_df_to_excel(
            df_hasil, sheet_name="Hasil Nilai TO"
        )
        st.download_button(
            label="Download Hasil Nilai",
            data=excel_bytes_to,
            file_name="Hasil_Nilai_Try_Out.xlsx",
            key="download_to",
        )

# ==========================================
# 3. TAB ABSENSI
# ==========================================
with tab_kehadiran:
    st.header("Ekstrak Kehadiran")
    st.info("Coming Soon")

# ==========================================
# 4. TAB BINSIK
# ==========================================
with tab_binsik:
    st.header("Ekstrak Nilai Binsik")
    st.info("Coming Soon")
