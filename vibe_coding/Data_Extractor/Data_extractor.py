import io
import pandas as pd
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

def process_to_tka(uploaded_siswa, uploaded_to, sheet_siswa, target_sheets):
    # 1. Load student data using simple selected_columns
    df_siswa_raw = pd.read_excel(uploaded_siswa, sheet_name=sheet_siswa, header=0)
    df_siswa = df_siswa_raw.dropna(how="all").copy()
    df_siswa.columns = df_siswa.columns.str.strip()

    selected_siswa_cols = ["NAMA SISWA", "NAMA AKUN TO"]
    
    # Extract columns & create join key
    df_hasil = df_siswa[selected_siswa_cols].copy()
    df_hasil["key_match"] = df_hasil["NAMA AKUN TO"].astype(str).str.strip().str.lower()

    # 2. Process score sheets
    excel_to = pd.ExcelFile(uploaded_to)
    selected_to_cols = ["NAMA AKUN", "TOTAL BENAR", "NILAI", "KATEGORI"]

    for sheet in target_sheets:
        if sheet in excel_to.sheet_names:
            df_nilai_raw = pd.read_excel(uploaded_to, sheet_name=sheet, header=7).dropna(how="all")
            df_nilai_raw.columns = df_nilai_raw.columns.str.strip()

            # Extract selected columns
            df_sub = df_nilai_raw[selected_to_cols].copy()
            df_sub["key_match"] = df_sub["NAMA AKUN"].astype(str).str.strip().str.lower()

            df_sub["TOTAL BENAR"] = (
                pd.to_numeric(df_sub["TOTAL BENAR"], errors="coerce")
                .round()
                .astype("Int64")
            )

            # Rename columns for the specific subtest sheet
            df_sub = df_sub.rename(
                columns={
                    "TOTAL BENAR": f"Jumlah_Nilai_Benar_{sheet}",
                    "NILAI": f"Nilai_{sheet}",
                    "KATEGORI": f"Kategori_{sheet}",
                }
            ).drop(columns=["NAMA AKUN"])

            # Merge with student list
            df_hasil = pd.merge(df_hasil, df_sub, on="key_match", how="left")

    # 3. Clean up final table
    df_hasil = df_hasil.drop(columns=["key_match"]).dropna(subset=["NAMA SISWA"])
    df_hasil = df_hasil.astype(object).fillna("-")
    df_hasil.index = range(1, len(df_hasil) + 1)

    return df_hasil
    
# --- NAVIGATION TABS ---
tab_db, tab_to_tka, tab_to_skd, tab_to_utbk, tab_kehadiran, tab_binsik = st.tabs(
    [
        "🔴 Ekstrak Database",
        "🟣 Ekstrak Nilai TO TKA",
        "🔴 Ekstrak Nilai TO SKD (coming soon)",
        "🟣 Ekstrak Nilai TO UTBK (coming soon)",
        "🔴 Ekstrak Absensi (coming soon)",
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
with tab_to_tka:
    st.header("Ekstrak Nilai TO TKA 🟣")

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
        # Sheet Selection UI
        excel_siswa = pd.ExcelFile(uploaded_siswa)
        excel_to = pd.ExcelFile(uploaded_to)

        selected_sheet_siswa = st.selectbox(
            "Pilih Sheet Nama Siswa:",
            excel_siswa.sheet_names,
            key="sheet_siswa_select",
        )

        st.subheader("Pilih Sheet Subtes Try Out")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            s1 = st.selectbox("Subtes 1:", excel_to.sheet_names, key="s1")
        with col_s2:
            s2 = st.selectbox("Subtes 2:", excel_to.sheet_names, key="s2")
        with col_s3:
            s3 = st.selectbox("Subtes 3:", excel_to.sheet_names, key="s3")

        # Process and Output
        df_hasil = process_to_tka(
            uploaded_siswa, uploaded_to, selected_sheet_siswa, [s1, s2, s3]
        )

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

with tab_to_skd:
    st.header("Ekstrak Nilai SKD")
    st.info("Coming Soon")

with tab_to_utbk:
    st.header("Ekstrak Nilai UTBK")
    st.info("Coming Soon")

with tab_kehadiran:
    st.header("Ekstrak Kehadiran")
    st.info("Coming Soon")

with tab_binsik:
    st.header("Ekstrak Nilai Binsik")
    st.info("Coming Soon")
