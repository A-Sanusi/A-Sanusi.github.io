import io
import numpy as np
import pandas as pd
import scipy.stats as stats
import streamlit as st
from fungsi_scoring.clean_question_id import clean_question_id
from fungsi_scoring.kalkulasi import (
    score_eap_3pl,
    process_nilai,
)

# ============================================================
# 1. CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Skoring IRT 3PL per Parameter",
    layout="wide"
)

st.link_button(
    "Menu",
    "https://a-sanusi.github.io/vibe_coding/vibe_coding.html"
)

st.title("IRT UTBK (untuk saat ini)")

D = 1.702
TARGET_MEAN = 500.0
TARGET_SD = 75.0
MIN_SCORE = 0.0
MAX_SCORE = 1000.0

# ============================================================
# 3. FILE UPLOADERS
# ============================================================

col1, col2 = st.columns(2)

with col1:
    uploaded_file = st.file_uploader(
        "1. Upload Jawaban Siswa",
        type=["xlsx", "xls", "xlsm"]
    )

with col2:
    uploaded_files_param = st.file_uploader(
        "2. Upload Parameter Try Out",
        type=["xlsx", "xls", "xlsm"],
        accept_multiple_files=True
    )

if uploaded_file is None or not uploaded_files_param:
    st.info("Silakan upload file jawaban dan minimal satu file parameter Excel untuk melanjutkan.")
    st.stop()


# ============================================================
# 4. LOAD RESPONSE DATA
# ============================================================

try:
    excel_file = pd.ExcelFile(uploaded_file)

    selected_sheet = st.selectbox(
        "Pilih Sheet Jawaban:",
        excel_file.sheet_names,
        key="sheet_resp"
    )

    df_resp_raw = pd.read_excel(
        excel_file,
        sheet_name=selected_sheet,
        header=1
    )

except Exception as e:
    st.error(f"Gagal membaca file jawaban: {e}")
    st.stop()

df_resp = df_resp_raw.dropna(how="all").reset_index(drop=True).copy()

if df_resp.empty:
    st.error("Sheet jawaban tidak memiliki data.")
    st.stop()

if len(df_resp.columns) < 4:
    st.error("Format sheet jawaban tidak sesuai. Diperlukan kolom Nama, Cabang, satu kolom tambahan, dan kolom-kolom soal.")
    st.stop()

test_taker_col = df_resp.columns[0]
cabang_col_name = df_resp.columns[1]
raw_q_cols = df_resp.columns[3:]

if len(raw_q_cols) == 0:
    st.error("Kolom soal tidak ditemukan mulai kolom keempat.")
    st.stop()


# ============================================================
# 5. CONFIGURE PARAMETER FILES & SHEETS INDIVIDUALLY
# ============================================================

subtest_configs = []

st.subheader("Pengaturan Sheet untuk Setiap File Parameter")
for idx, param_file in enumerate(uploaded_files_param):
    try:
        excel_p = pd.ExcelFile(param_file)
        
        selected_sheet_p = st.selectbox(
            f"Pilih Sheet untuk file: {param_file.name}",
            excel_p.sheet_names,
            key=f"sheet_param_{idx}"
        )

        df_p_raw = pd.read_excel(
            excel_p,
            sheet_name=selected_sheet_p
        )

        if df_p_raw.shape[1] < 7:
            st.error(f"Format file {param_file.name} (sheet: {selected_sheet_p}) tidak sesuai. Diperlukan minimal tujuh kolom.")
            st.stop()

        df_p_sub = df_p_raw.iloc[:, [2, 3, 4, 5, 6]].copy()
        df_p_sub.columns = [
            "Nomor Soal",
            "Question ID",
            "Discrimination",
            "Difficulty",
            "Guessing"
        ]
        
        df_p_sub["Clean_ID"] = clean_question_id(
            df_p_sub["Question ID"]
        ).to_numpy()

        df_p_sub = df_p_sub.dropna(subset=["Clean_ID"]).copy()

        label = f"{param_file.name} ({selected_sheet_p})"

        subtest_configs.append({
            "label": label,
            "df_param": df_p_sub
        })

    except Exception as e:
        st.error(f"Gagal membaca file parameter {param_file.name}: {e}")
        st.stop()

if not subtest_configs:
    st.warning("Pilih minimal satu konfigurasi parameter untuk melanjutkan.")
    st.stop()


# ============================================================
# 6. EXECUTE IRT SCORING VIA process_nilai() & RENDER RESULTS
# ============================================================

resp_q_ids = clean_question_id(raw_q_cols)

if resp_q_ids.isna().any() or resp_q_ids.duplicated().any():
    st.error("Terdapat Question ID kosong atau duplikat pada header kolom jawaban.")
    st.stop()

resp_id_map = dict(zip(raw_q_cols, resp_q_ids))

st.divider()
st.subheader("Parameter IRT")

df_results = process_nilai(
    df_resp=df_resp,
    subtest_configs=subtest_configs,
    resp_id_map=resp_id_map,
    raw_q_cols=raw_q_cols,
    test_taker_col=test_taker_col,
    cabang_col_name=cabang_col_name,
    D=D,
    TARGET_MEAN=TARGET_MEAN,
    TARGET_SD=TARGET_SD,
    MIN_SCORE=MIN_SCORE,
    MAX_SCORE=MAX_SCORE
)

if df_results.empty:
    st.error("Tidak ada parameter valid yang berhasil diskoring.")
    st.stop()

# Render complete table with all parameters
st.dataframe(
    df_results,
    use_container_width=True,
    hide_index=True
)

st.divider()
st.subheader("Nilai Benar & IRT")

# Dynamically gather student info and all distinct Skor IRT columns
jumlah_benar_cols = [col for col in df_results.columns if col.startswith("Jumlah Benar")]
skor_irt_cols = [col for col in df_results.columns if col.startswith("Skor IRT")]
df_results["total_skor_IRT"] = df_results[skor_irt_cols].sum(axis=1)
df_results["rata-rata_IRT"] = df_results["total_skor_IRT"]/7

# Combine them in the desired order
irt_score_columns = ["Nama", "Cabang"] + jumlah_benar_cols + skor_irt_cols + ["total_skor_IRT", "rata-rata_IRT"]

st.dataframe(
    df_results[irt_score_columns],
    use_container_width=True,
    hide_index=True
)

st.divider()
st.subheader("Nilai IRT")

irt_2_score_columns = ["Nama", "Cabang"] + skor_irt_cols + ["total_skor_IRT", "rata-rata_IRT"]

st.dataframe(
    df_results[irt_2_score_columns],
    use_container_width=True,
    hide_index=True
)

# ============================================================
# 7. EXPORT RESULTS TO EXCEL
# ============================================================

buffer = io.BytesIO()

try:
    with pd.ExcelWriter(
        buffer,
        engine="openpyxl"
    ) as writer:
        df_results.to_excel(
            writer,
            sheet_name="Hasil_Skor_Per_Parameter",
            index=False
        )

except Exception as e:
    st.error(f"Gagal membuat file Excel: {e}")
    st.stop()

output_filename = (
    f"{uploaded_file.name.rsplit('.', 1)[0]} "
    "IRT_SCORES_PER_PARAMETER.xlsx"
)

st.download_button(
    label="Download Hasil Skoring Excel",
    data=buffer.getvalue(),
    file_name=output_filename,
)
