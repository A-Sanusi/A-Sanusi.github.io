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
    page_title="Skoring IRT 3PL per Parameter",
    layout="wide"
)

st.link_button(
    "Menu",
    "https://a-sanusi.github.io/vibe_coding/vibe_coding.html"
)

st.title("Skoring IRT 3PL per Parameter / Subtes")

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
# 5. CONFIGURE PARAMETER FILES & SHEETS INDIVIDUALLY
# ============================================================

subtest_configs = []

st.subheader("Pengaturan Sheet untuk Setiap File Parameter")
for idx, param_file in enumerate(uploaded_files_param):
    try:
        excel_p = pd.ExcelFile(param_file)
        
        # Single sheet selection per uploaded file using st.selectbox
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
                f"Format file {param_file.name} (sheet: {selected_sheet_p}) tidak sesuai. "
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
        
        df_p_sub["Clean_ID"] = clean_question_id(
            df_p_sub["Question ID"]
        ).to_numpy()

        df_p_sub = df_p_sub.dropna(subset=["Clean_ID"]).copy()

        # Unique label representing this distinct parameter set
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
# 6. CALCULATE IRT SCORES INDEPENDENTLY FOR EACH PARAMETER SET
# ============================================================

resp_q_ids = clean_question_id(raw_q_cols)

if resp_q_ids.isna().any() or resp_q_ids.duplicated().any():
    st.error("Terdapat Question ID kosong atau duplikat pada header kolom jawaban.")
    st.stop()

resp_id_map = dict(zip(raw_q_cols, resp_q_ids))

# Prepare base student results dataframe
valid_mask = df_resp[test_taker_col].notna() & df_resp[test_taker_col].astype(str).str.strip().ne("")
df_results = pd.DataFrame({
    "Nama": df_resp.loc[valid_mask, test_taker_col],
    "Cabang": df_resp.loc[valid_mask, cabang_col_name]
}).reset_index(drop=True)

df_resp_valid = df_resp.loc[valid_mask].reset_index(drop=True)

st.divider()
st.subheader("Hasil Skoring per Parameter")

scoring_success = False

for config in subtest_configs:
    label = config["label"]
    df_p = config["df_param"]
    param_id_set = set(df_p["Clean_ID"])

    matched_q_cols = [
        col for col in raw_q_cols if resp_id_map[col] in param_id_set
    ]

    if not matched_q_cols:
        st.warning(f"Tidak ada soal yang cocok dengan parameter: {label}")
        continue

    matched_param_ids = [resp_id_map[col] for col in matched_q_cols]
    df_p_indexed = df_p.set_index("Clean_ID")
    df_p_aligned = df_p_indexed.loc[matched_param_ids].copy()

    a = pd.to_numeric(df_p_aligned["Discrimination"], errors="coerce").to_numpy(dtype=float)
    b = pd.to_numeric(df_p_aligned["Difficulty"], errors="coerce").to_numpy(dtype=float)
    c = pd.to_numeric(df_p_aligned["Guessing"], errors="coerce").to_numpy(dtype=float)

    valid_params = (
        np.isfinite(a) & np.isfinite(b) & np.isfinite(c) & (a > 0) & (c >= 0) & (c < 1)
    )

    if not valid_params.all():
        st.error(f"Parameter IRT tidak valid pada parameter: {label}")
        continue

    response_df = df_resp_valid[matched_q_cols].apply(pd.to_numeric, errors="coerce")
    X = response_df.fillna(0).to_numpy(dtype=float)

    if X.shape[0] == 0:
        continue

    try:
        theta_estimates, se_estimates = score_eap_3pl(
            X=X, a=a, b=b, c=c, D=D, grid_points=401
        )

        raw_scores = np.sum(X, axis=1).astype(int)
        total_items = len(matched_q_cols)
        pct_correct = np.round((raw_scores / total_items) * 100, 2)

        scaled_scores = [
            np.clip(round(TARGET_MEAN + TARGET_SD * float(th), 2), MIN_SCORE, MAX_SCORE)
            for th in theta_estimates
        ]

        # Add distinct columns for this specific parameter set
        df_results[f"Jumlah Benar ({label})"] = raw_scores
        df_results[f"Persentase ({label})"] = pct_correct
        df_results[f"Theta ({label})"] = np.round(theta_estimates, 4)
        df_results[f"SE ({label})"] = np.round(se_estimates, 4)
        df_results[f"Skor IRT ({label})"] = scaled_scores

        scoring_success = True

    except Exception as e:
        st.error(f"Gagal menghitung skor untuk parameter {label}: {e}")

if not scoring_success:
    st.error("Tidak ada parameter valid yang berhasil diskoring.")
    st.stop()

st.dataframe(
    df_results,
    use_container_width=True,
    hide_index=True
)

st.divider()
st.subheader("Hasil IRT")
st.datafreame(
    df_results,
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
    mime=(
        "application/vnd.openxmlformats-officedocument."
        "spreadsheetml.sheet"
    )
)
