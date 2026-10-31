import io
import numpy as np
import pandas as pd
import scipy.stats as stats
import streamlit as st
from scipy.special import logsumexp

# ============================================================
# 1. CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Skoring IRT 3PL",
    layout="wide"
)

st.link_button(
    "Menu",
    "https://a-sanusi.github.io/vibe_coding/vibe_coding.html"
)

st.title("Skoring IRT 3PL")

D = 1.702
TARGET_MEAN = 500.0
TARGET_SD = 75.0
MIN_SCORE = 200.0
MAX_SCORE = 800.0


# ============================================================
# 2. HELPER FUNCTIONS
# ============================================================

def clean_question_id(series_or_columns):
    """Normalize Question IDs for consistent matching."""
    return (
        pd.Series(series_or_columns)
        .astype("string")
        .str.replace(r"^ID\s*:\s*", "", regex=True)
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
        .replace("", pd.NA)
    )


def score_eap_3pl(
    X,
    a,
    b,
    c,
    D=1.702,
    grid_points=401
):
    """
    Calculate EAP theta estimates and posterior SDs
    using the 3PL IRT model.

    X: Binary response matrix (students x items).
    a: Item discrimination parameters.
    b: Item difficulty parameters.
    c: Item guessing parameters.

    Returns:
        theta_eap: EAP ability estimates.
        se_eap: Posterior standard deviations.
    """

    X = np.asarray(X, dtype=float)
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    c = np.asarray(c, dtype=float)

    if X.ndim != 2:
        raise ValueError("Matriks jawaban harus dua dimensi.")

    n_students, n_items = X.shape

    if n_students == 0 or n_items == 0:
        raise ValueError(
            "Matriks jawaban tidak boleh kosong."
        )

    if not (len(a) == len(b) == len(c) == n_items):
        raise ValueError(
            "Jumlah parameter tidak sama dengan jumlah soal."
        )

    if grid_points < 2:
        raise ValueError(
            "grid_points minimal harus 2."
        )

    if not np.isfinite(X).all():
        raise ValueError(
            "Matriks jawaban mengandung nilai tidak valid."
        )

    if not np.isin(X, [0, 1]).all():
        raise ValueError(
            "Jawaban hanya boleh berupa 0 dan 1."
        )

    # Validate IRT parameters.
    valid_params = (
        np.isfinite(a)
        & np.isfinite(b)
        & np.isfinite(c)
        & (a > 0)
        & (c >= 0)
        & (c < 1)
    )

    if not valid_params.all():
        raise ValueError(
            "Parameter IRT tidak valid. "
            "Pastikan a > 0, b bernilai finite, "
            "dan 0 <= c < 1."
        )

    # Theta grid and standard normal prior.
    theta_grid = np.linspace(-4.0, 4.0, grid_points)

    log_prior = stats.norm.logpdf(theta_grid, loc=0, scale=1)

    # 3PL probabilities, using a stable logistic function.
    z = D * a[:, None] * (
        theta_grid[None, :] - b[:, None]
    )

    logistic_prob = stats.logistic.cdf(z)

    P = c[:, None] + (
        1.0 - c[:, None]
    ) * logistic_prob

    P = np.clip(P, 1e-12, 1.0 - 1e-12)

    log_P = np.log(P)
    log_Q = np.log1p(-P)

    # Log likelihood: students x theta grid.
    log_L = (
        X @ log_P
        + (1.0 - X) @ log_Q
    )

    # Posterior proportional to likelihood * prior.
    log_posterior = log_L + log_prior[None, :]

    # Normalize using log-sum-exp for numerical stability.
    log_normalizer = logsumexp(
        log_posterior,
        axis=1,
        keepdims=True
    )

    posterior = np.exp(
        log_posterior - log_normalizer
    )

    # EAP theta and posterior standard deviation.
    theta_eap = np.sum(
        posterior * theta_grid[None, :],
        axis=1
    )

    variance = np.sum(
        posterior
        * (
            theta_grid[None, :]
            - theta_eap[:, None]
        ) ** 2,
        axis=1
    )

    se_eap = np.sqrt(
        np.maximum(variance, 0.0)
    )

    return theta_eap, se_eap


# ============================================================
# 3. FILE UPLOADERS (MULTIPLE PARAMETER FILES SUPPORTED)
# ============================================================

col1, col2 = st.columns(2)

with col1:
    uploaded_file = st.file_uploader(
        "1. Upload Jawaban Siswa",
        type=["xlsx", "xls", "xlsm"]
    )

with col2:
    uploaded_files_param = st.file_uploader(
        "2. Upload Parameter Try Out (Bisa Pilih Banyak File)",
        type=["xlsx", "xls", "xlsm"],
        accept_multiple_files=True
    )

if uploaded_file is None or not uploaded_files_param:
    st.info(
        "Silakan upload file jawaban dan minimal satu file parameter Excel untuk melanjutkan."
    )
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

# Remove completely empty rows and RESET INDEX.
df_resp = (
    df_resp_raw
    .dropna(how="all")
    .reset_index(drop=True)
    .copy()
)

if df_resp.empty:
    st.error("Sheet jawaban tidak memiliki data.")
    st.stop()

if len(df_resp.columns) < 4:
    st.error(
        "Format sheet jawaban tidak sesuai. "
        "Diperlukan kolom Nama, Cabang, satu kolom tambahan, "
        "dan kolom-kolom soal."
    )
    st.stop()

test_taker_col = df_resp.columns[0]
cabang_col_name = df_resp.columns[1]
raw_q_cols = df_resp.columns[3:]

if len(raw_q_cols) == 0:
    st.error(
        "Kolom soal tidak ditemukan mulai kolom keempat."
    )
    st.stop()


# ============================================================
# 5. LOAD & COMBINE MULTIPLE ITEM PARAMETER FILES
# ============================================================

param_dfs = []

st.subheader("Pengaturan Sheet Parameter")
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
            st.error(
                f"Format file {param_file.name} tidak sesuai. "
                "Diperlukan minimal tujuh kolom."
            )
            st.stop()

        df_p_sub = df_p_raw.iloc[:, [2, 3, 4, 5, 6]].copy()
        df_p_sub.columns = [
            "Nomor Soal",
            "Question ID",
            "Discrimination",
            "Difficulty",
            "Guessing"
        ]
        param_dfs.append(df_p_sub)

    except Exception as e:
        st.error(f"Gagal membaca file parameter {param_file.name}: {e}")
        st.stop()

# Combine all loaded parameter dataframes into one
df_param = pd.concat(param_dfs, ignore_index=True)

df_param["Clean_ID"] = clean_question_id(
    df_param["Question ID"]
).to_numpy()

# Remove rows without a Question ID.
df_param = df_param.dropna(
    subset=["Clean_ID"]
).copy()

if df_param.empty:
    st.error(
        "Question ID tidak ditemukan pada file-file parameter yang diupload."
    )
    st.stop()

# Check duplicate normalized IDs across all parameter files.
if df_param["Clean_ID"].duplicated().any():
    duplicates = (
        df_param.loc[
            df_param["Clean_ID"].duplicated(keep=False),
            "Clean_ID"
        ]
        .unique()
        .tolist()
    )

    st.error(
        "Terdapat Question ID duplikat antar file parameter: "
        + ", ".join(map(str, duplicates[:20]))
    )
    st.stop()


# ============================================================
# 6. MATCH QUESTION IDS
# ============================================================

resp_q_ids = clean_question_id(raw_q_cols)

# Check IDs that are blank or duplicated after normalization.
if resp_q_ids.isna().any():
    st.error(
        "Terdapat Question ID kosong pada header kolom jawaban."
    )
    st.stop()

if resp_q_ids.duplicated().any():
    duplicates = (
        resp_q_ids[
            resp_q_ids.duplicated(keep=False)
        ]
        .unique()
        .tolist()
    )

    st.error(
        "Terdapat Question ID duplikat pada sheet jawaban: "
        + ", ".join(map(str, duplicates[:20]))
    )
    st.stop()

resp_id_map = dict(zip(raw_q_cols, resp_q_ids))

param_id_set = set(df_param["Clean_ID"])

matched_q_cols = [
    col
    for col in raw_q_cols
    if resp_id_map[col] in param_id_set
]

if not matched_q_cols:
    st.error(
        "Gagal mencocokkan Question ID antara "
        "sheet jawaban dan file-file parameter."
    )
    st.stop()

matched_param_ids = [
    resp_id_map[col]
    for col in matched_q_cols
]

df_param_indexed = df_param.set_index("Clean_ID")

df_param_aligned = df_param_indexed.loc[
    matched_param_ids
].copy()

# Report unmatched columns.
unmatched_q_cols = [
    col
    for col in raw_q_cols
    if col not in matched_q_cols
]

st.success(
    f"Berhasil mencocokkan {len(matched_q_cols)} soal dari total {len(uploaded_files_param)} file parameter."
)

if unmatched_q_cols:
    st.warning(
        f"{len(unmatched_q_cols)} kolom soal tidak memiliki "
        "parameter yang cocok dan tidak digunakan dalam skoring."
    )


# ============================================================
# 7. VALIDATE ITEM PARAMETERS
# ============================================================

a = pd.to_numeric(
    df_param_aligned["Discrimination"],
    errors="coerce"
).to_numpy(dtype=float)

b = pd.to_numeric(
    df_param_aligned["Difficulty"],
    errors="coerce"
).to_numpy(dtype=float)

c = pd.to_numeric(
    df_param_aligned["Guessing"],
    errors="coerce"
).to_numpy(dtype=float)

valid_params = (
    np.isfinite(a)
    & np.isfinite(b)
    & np.isfinite(c)
    & (a > 0)
    & (c >= 0)
    & (c < 1)
)

if not valid_params.all():
    bad_ids = np.asarray(
        matched_param_ids,
        dtype=object
    )[~valid_params]

    st.error(
        "Parameter IRT tidak valid pada Question ID: "
        + ", ".join(map(str, bad_ids[:20]))
        + ". Pastikan a > 0, b finite, dan 0 <= c < 1."
    )
    st.stop()


# ============================================================
# 8. PREPARE BINARY RESPONSE MATRIX
# ============================================================

response_df = df_resp[matched_q_cols].apply(
    pd.to_numeric,
    errors="coerce"
)

# Detect nonnumeric values separately from genuinely blank cells.
raw_response_df = df_resp[matched_q_cols]

nonnumeric = (
    raw_response_df.notna()
    & response_df.isna()
)

if nonnumeric.any().any():
    bad_columns = (
        nonnumeric.columns[
            nonnumeric.any(axis=0)
        ]
        .astype(str)
        .tolist()
    )

    st.error(
        "Ditemukan jawaban nonnumerik pada kolom: "
        + ", ".join(bad_columns[:20])
        + ". Konversikan jawaban menjadi 0 atau 1 terlebih dahulu."
    )
    st.stop()

# Reject values other than 0 or 1.
invalid_values = (
    response_df.notna()
    & ~response_df.isin([0, 1])
)

if invalid_values.any().any():
    bad_columns = (
        invalid_values.columns[
            invalid_values.any(axis=0)
        ]
        .astype(str)
        .tolist()
    )

    st.error(
        "Ditemukan nilai jawaban selain 0 dan 1 pada kolom: "
        + ", ".join(bad_columns[:20])
    )
    st.stop()

# Blank responses are treated as incorrect (0).
X = response_df.fillna(0).to_numpy(dtype=float)

if X.shape[0] == 0:
    st.error("Tidak ada data siswa untuk diskoring.")
    st.stop()


# ============================================================
# 9. CALCULATE EAP SCORES
# ============================================================

st.divider()
st.subheader("Hasil Skoring")

try:
    with st.spinner("Menghitung skor IRT EAP..."):
        theta_estimates, se_estimates = score_eap_3pl(
            X=X,
            a=a,
            b=b,
            c=c,
            D=D,
            grid_points=401
        )

except Exception as e:
    st.error(f"Gagal menghitung skor IRT: {e}")
    st.stop()


# ============================================================
# 10. BUILD STUDENT RESULTS (MULTIPLE PARAMETERS)
# ============================================================

results = []
total_items = len(matched_q_cols)

for pos in range(len(df_resp)):
    row = df_resp.iloc[pos]
    test_taker = row[test_taker_col]

    # Skip rows without a student name.
    if pd.isna(test_taker) or not str(test_taker).strip():
        continue

    cabang_val = row[cabang_col_name]

    raw_score = int(np.sum(X[pos]))
    pct_correct = round((raw_score / total_items) * 100, 2)
    theta_val = float(theta_estimates[pos])
    se_val = float(se_estimates[pos])

    # Linear transformation from theta to reporting scale.
    scaled_score = np.clip(
        round(
            TARGET_MEAN + TARGET_SD * theta_val,
            2
        ),
        MIN_SCORE,
        MAX_SCORE
    )

    results.append({
        "Nama": test_taker,
        "Cabang": cabang_val,
        "Jumlah Soal": total_items,
        "Banyak Soal Benar": raw_score,
        "Persentase Benar (%)": pct_correct,
        "Estimasi Theta (Ability)": round(theta_val, 4),
        "SE Theta (Error)": round(se_val, 4),
        "Skor IRT": scaled_score
    })

if not results:
    st.warning(
        "Tidak ada data siswa yang valid untuk diskoring."
    )
    st.stop()

df_results = pd.DataFrame(results)

st.dataframe(
    df_results,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# 11. EXPORT RESULTS TO MULTI-SHEET EXCEL
# ============================================================

buffer = io.BytesIO()

try:
    with pd.ExcelWriter(
        buffer,
        engine="openpyxl"
    ) as writer:
        # Sheet 1: Student IRT Results
        df_results.to_excel(
            writer,
            sheet_name="Hasil_Skor_Siswa",
            index=False
        )

        # Sheet 2: Combined Item Parameters (a, b, c) from all uploaded files
        df_param_aligned_export = df_param_aligned.copy().reset_index()
        df_param_aligned_export.to_excel(
            writer,
            sheet_name="Parameter_Soal",
            index=False
        )

except Exception as e:
    st.error(f"Gagal membuat file Excel: {e}")
    st.stop()

output_filename = (
    f"{uploaded_file.name.rsplit('.', 1)[0]} "
    "IRT_3PL_FULL_PARAMS.xlsx"
)

st.download_button(
    label="Download Hasil & Parameter Excel",
    data=buffer.getvalue(),
    file_name=output_filename,
    mime=(
        "application/vnd.openxmlformats-officedocument."
        "spreadsheetml.sheet"
    )
)
