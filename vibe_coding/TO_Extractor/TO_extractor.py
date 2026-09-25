import io
import numpy as np
import pandas as pd
import scipy.stats as stats
import streamlit as st

st.set_page_config(page_title="TRIM TO", layout="wide")
st.title("TRIM Try Out")

col1, col2 = st.columns(2)

with col1:
  uploaded_file = st.file_uploader(
      "Upload File Excel Nama Siswa", type=["xlsx", "xls", "xlsm"]
  )

with col2:
  uploaded_file_2 = st.file_uploader(
      "Upload File Try Out", type=["xlsx", "xls", "xlsm"]
  )

if uploaded_file is None or uploaded_file_2 is None:
  st.stop()

# 1. Baca data siswa
excel_file = pd.ExcelFile(uploaded_file)
selected_sheet = st.selectbox(
    "Pilih Sheet Nama: ", excel_file.sheet_names, key="sheet_siswa"
)

df_siswa_raw = pd.read_excel(uploaded_file, sheet_name=selected_sheet, header=0)
df_siswa = df_siswa_raw.dropna(how="all").copy()

nama_siswa_col = df_siswa.columns[1]
nama_akun_col = df_siswa.columns[2]

# Buat kunci pencocokan (lowercase & hapus spasi tambahan)
df_siswa["key_match"] = (
    df_siswa[nama_akun_col].astype(str).str.strip().str.lower()
)

# 2. Proses pengambil nilai dari sheet TORMA 1, TORBI 1, TORBIG 1
excel_file_2 = pd.ExcelFile(uploaded_file_2)
target_sheets = ["TORMA 1", "TORBI 1", "TORBIG 1"]

# DataFrame hasil gabungan
df_hasil = df_siswa[[nama_siswa_col, nama_akun_col, "key_match"]].copy()

for sheet in target_sheets:
  if sheet in excel_file_2.sheet_names:
    # Baca data nilai per sheet
    df_nilai_raw = pd.read_excel(
        uploaded_file_2, sheet_name=sheet, header=7
    ).dropna(how="all")

    nama_akun_2_col = df_nilai_raw.columns[1]  # Kolom Nama Siswa/Akun
    nilai_TO_col = df_nilai_raw.columns[4]  # Kolom Nilai

    # Buat kunci pencocokan
    df_nilai_raw["key_match"] = (
        df_nilai_raw[nama_akun_2_col].astype(str).str.strip().str.lower()
    )

    # Ambil kolom kunci dan nilai, lalu hapus duplikasi jika ada
    df_sub = df_nilai_raw[["key_match", nilai_TO_col]].drop_duplicates(
        subset=["key_match"]
    )
    df_sub = df_sub.rename(columns={nilai_TO_col: f"Nilai_{sheet}"})

    # Gabungkan ke DataFrame utama berdasarkan kunci
    df_hasil = pd.merge(df_hasil, df_sub, on="key_match", how="left")

# Hapus kolom kunci bantu
df_hasil = df_hasil.drop(columns=["key_match"]).dropna(
    subset=[nama_siswa_col]
)

# 3. Tampilkan Hasil
st.subheader("Tabel Nilai Siswa")
st.dataframe(df_hasil, use_container_width=True)

# 4. Fitur Tambahan: Pilih Siswa untuk Melihat Detail Nilai
st.subheader("Detail Nilai Per Siswa")
selected_student = st.selectbox(
    "Pilih Nama Siswa:", df_hasil[nama_siswa_col].unique()
)

student_data = df_hasil[df_hasil[nama_siswa_col] == selected_student].iloc[0]

col_a, col_b, col_c = st.columns(3)
with col_a:
  st.metric("TORMA 1", student_data.get("Nilai_TORMA 1", "-"))
with col_b:
  st.metric("TORBI 1", student_data.get("Nilai_TORBI 1", "-"))
with col_c:
  st.metric("TORBIG 1", student_data.get("Nilai_TORBIG 1", "-"))
