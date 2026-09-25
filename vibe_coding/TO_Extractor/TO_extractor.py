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

# 2. Proses pengambil nilai dari sheet sheet_siswa_1, sheet_siswa_2, sheet_siswa_3
excel_file_2 = pd.ExcelFile(uploaded_file_2)
selected_sheet_1 = st.selectbox(
    "Pilih Sheet Nama: ", excel_file_2.sheet_names, key="sheet_siswa_1"
)
selected_sheet_2 = st.selectbox(
    "Pilih Sheet Nama: ", excel_file_2.sheet_names, key="sheet_siswa_2"
)
selected_sheet_3 = st.selectbox(
    "Pilih Sheet Nama: ", excel_file_2.sheet_names, key="sheet_siswa_3"
)

target_sheets = [selected_sheet_1, selected_sheet_2, selected_sheet_3]

# DataFrame hasil gabungan
df_hasil = df_siswa[[nama_siswa_col, nama_akun_col, "key_match"]].copy()

for sheet in target_sheets:
    if sheet in excel_file_2.sheet_names:
        # Baca data nilai per sheet
        df_nilai_raw = pd.read_excel(
            uploaded_file_2, sheet_name=sheet, header=7
        ).dropna(how="all")

        nama_akun_2_col = df_nilai_raw.columns[1]   # Kolom Nama Siswa/Akun
        Total_Benar_TO_col = df_nilai_raw.columns[3] # Kolom Jumlah Benar
        nilai_TO_col = df_nilai_raw.columns[4]       # Kolom Nilai
        kategori_TO_col = df_nilai_raw.columns[5]    # Kategori Nilai
        
        # Buat kunci pencocokan
        df_nilai_raw["key_match"] = (
            df_nilai_raw[nama_akun_2_col].astype(str).str.strip().str.lower()
        )
        
        # Ambil Nilai
        df_sub = df_nilai_raw[["key_match", nilai_TO_col]].drop_duplicates(
            subset=["key_match"]
        )
        df_sub = df_sub.rename(columns={nilai_TO_col: f"Nilai_{sheet}"})

        # Ambil Kategori
        df_sub_2 = df_nilai_raw[["key_match", kategori_TO_col]].drop_duplicates(
            subset=["key_match"]
        )
        df_sub_2 = df_sub_2.rename(columns={kategori_TO_col: f"Kategori_{sheet}"})
        
        # Ambil & Round Jumlah Benar
        df_sub_3 = df_nilai_raw[["key_match", Total_Benar_TO_col]].drop_duplicates(
            subset=["key_match"]
        ).copy()
        
        df_sub_3[Total_Benar_TO_col] = (
            pd.to_numeric(df_sub_3[Total_Benar_TO_col], errors="coerce")
            .round()
            .astype("Int64")
        )
        
        df_sub_3 = df_sub_3.rename(columns={Total_Benar_TO_col: f"Jumlah_Nilai_Benar_{sheet}"})
        
        # Gabungkan ke DataFrame utama
        df_hasil = pd.merge(df_hasil, df_sub_3, on="key_match", how="left")
        df_hasil = pd.merge(df_hasil, df_sub, on="key_match", how="left")
        df_hasil = pd.merge(df_hasil, df_sub_2, on="key_match", how="left")
        
# Hapus kolom kunci bantu dan ganti null dengan "-"
df_hasil = df_hasil.drop(columns=["key_match"]).dropna(subset=[nama_siswa_col])

# Convert to object before fillna to accept "-" alongside integers
df_hasil = df_hasil.astype(object).fillna("-")
df_hasil.index = range(1, len(df_hasil) + 1)

# 3. Tampilkan Hasil & Fitur Export
st.subheader("Tabel Nilai Siswa")

# Fungsi untuk mengubah DataFrame ke stream Bytes Excel
def convert_df_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Hasil Nilai TO")
    return output.getvalue()

# Konversi DataFrame ke Excel
df_hasil_2 = pd.merge(df_hasil.index, df_hasil, on="key_match", how="left")
excel_bytes = convert_df_to_excel(df_hasil_2)

st.dataframe(df_hasil_2, use_container_width=True)

# 4. Fitur Tambahan: Pilih Siswa untuk Melihat Detail Nilai
st.subheader("Detail Nilai Per Siswa")
selected_student = st.selectbox(
    "Pilih Nama Siswa:", df_hasil[nama_siswa_col].unique()
)

student_data = df_hasil[df_hasil[nama_siswa_col] == selected_student].iloc[0]

col_a, col_b, col_c = st.columns(3)
with col_a:
    st.metric(
        f"{selected_sheet_1}", student_data.get(f"Nilai_{selected_sheet_1}", "-")
    )
with col_b:
    st.metric(
        f"{selected_sheet_2}", student_data.get(f"Nilai_{selected_sheet_2}", "-")
    )
with col_c:
    st.metric(
        f"{selected_sheet_3}", student_data.get(f"Nilai_{selected_sheet_3}", "-")
    )

# Tombol Download Excel
st.download_button(
    label="Download Hasil Nilai",
    data=excel_bytes,
    file_name="Hasil_Nilai_Try_Out.xlsx",
)
