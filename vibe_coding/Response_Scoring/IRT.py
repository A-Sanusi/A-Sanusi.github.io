import io
import numpy as np
import pandas as pd
import scipy.stats as stats
import streamlit as st

st.set_page_config(page_title="Skoring IRT 3PL", layout="wide")
st.title("Skoring IRT (3PL Model)")

# --- Sidebar Configuration ---
st.sidebar.header("Konfigurasi IRT")

# 1. Scaling Constant D
metric_choice = st.sidebar.radio(
    "Metrik Parameter (D):",
    options=["Normal Metric (D = 1.702) - Standard Bilog/R", "Logistic Metric (D = 1.0)"],
    index=0,
    help="Gunakan D=1.702 jika parameter dikalibrasi di software seperti Bilog-MG atau R mirt (default)."
)
D = 1.702 if "1.702" in metric_choice else 1.0

# 2. Estimation Method
est_method = st.sidebar.selectbox(
    "Metode Estimasi Theta:",
    options=["EAP (Expected A Posteriori) - Recommended", "MAP (Maximum A Posteriori)"],
    index=0,
    help="EAP menggunakan integrasi grid Bayesian; sangat stabil dan standar industri."
)

# 3. Score Transformation Settings
st.sidebar.subheader("Transformasi Skor")
target_mean = st.sidebar.number_input("Target Mean Score", value=500.0, step=10.0)
target_sd = st.sidebar.number_input("Target SD Score", value=75.0, step=5.0)
min_score = st.sidebar.number_input("Batas Skor Minimum", value=200.0, step=10.0)
max_score = st.sidebar.number_input("Batas Skor Maksimum", value=800.0, step=10.0)


def clean_question_id(series_or_columns):
    """Normalize Question IDs for accurate matching."""
    return (
        pd.Series(series_or_columns)
        .astype(str)
        .str.replace(r"^ID\s*:\s*", "", regex=True)
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
    )


# --- 1. File Uploaders ---
col1, col2 = st.columns(2)

with col1:
    uploaded_file = st.file_uploader(
        "1. Upload Jawaban Siswa (Biner 1/0)", type=["xlsx", "xls", "xlsm"]
    )

with col2:
    uploaded_file_2 = st.file_uploader(
        "2. Upload Parameter Try Out", type=["xlsx", "xls", "xlsm"]
    )

if uploaded_file is None or uploaded_file_2 is None:
    st.info("Silakan upload kedua file Excel untuk melanjutkan.")
    st.stop()

# --- 2. Load Responses Sheet ---
excel_file = pd.ExcelFile(uploaded_file)
selected_sheet = st.selectbox(
    "Pilih Sheet Jawaban:", excel_file.sheet_names, key="sheet_resp"
)

df_resp_raw = pd.read_excel(uploaded_file, sheet_name=selected_sheet, header=1)
df_resp = df_resp_raw.dropna(how="all").copy()

test_taker_col = df_resp.columns[0]
cabang_col_name = df_resp.columns[1]
raw_q_cols = df_resp.columns[3:]

# --- 3. Load & Align Parameters ---
excel_file_2 = pd.ExcelFile(uploaded_file_2)
selected_sheet_2 = st.selectbox(
    "Pilih Sheet Parameter:", excel_file_2.sheet_names, key="sheet_param"
)
df_param_raw = pd.read_excel(uploaded_file_2, sheet_name=selected_sheet_2)

df_param = df_param_raw.iloc[:, [2, 3, 4, 5, 6]].copy()
df_param.columns = ["Nomor Soal", "Question ID", "Discrimination", "Difficulty", "Guessing"]
df_param["Clean_ID"] = clean_question_id(df_param["Question ID"])

# Match response columns with parameters using exact Question IDs
resp_q_ids = clean_question_id(raw_q_cols)
resp_id_map = dict(zip(raw_q_cols, resp_q_ids))

matched_q_cols = [col for col in raw_q_cols if resp_id_map[col] in set(df_param["Clean_ID"])]

if not matched_q_cols:
    st.error("Gagal mencocokkan Question ID antara sheet jawaban dan sheet parameter.")
    st.stop()

df_param_indexed = df_param.set_index("Clean_ID")
matched_param_ids = [resp_id_map[col] for col in matched_q_cols]
df_param_aligned = df_param_indexed.loc[matched_param_ids]

a = pd.to_numeric(df_param_aligned["Discrimination"], errors="coerce").values
b = pd.to_numeric(df_param_aligned["Difficulty"], errors="coerce").values
c = pd.to_numeric(df_param_aligned["Guessing"], errors="coerce").values

# Prepare binary response matrix (N_students x N_items)
X = (
    df_resp[matched_q_cols]
    .astype(str)
    .apply(lambda col: col.str.strip())
    .apply(pd.to_numeric, errors="coerce")
    .fillna(0)
    .values
)

# --- 4. IRT Engine (EAP & MAP Vectorized) ---
def compute_3pl_prob(theta_grid, a, b, c, D):
    """
    Computes 3PL item response probabilities over a grid of theta.
    Returns array of shape (N_items, N_grid)
    """
    # theta_grid: (N_grid,), a,b,c: (N_items,)
    # Output: (N_items, N_grid)
    exp_term = np.exp(-D * a[:, None] * (theta_grid[None, :] - b[:, None]))
    p = c[:, None] + (1.0 - c[:, None]) / (1.0 + exp_term)
    return np.clip(p, 1e-9, 1.0 - 1e-9)


def score_eap(X, a, b, c, D, grid_points=101):
    """
    Calculates Expected A Posteriori (EAP) ability estimates and SEs.
    Fully vectorized across all respondents.
    """
    theta_grid = np.linspace(-4.0, 4.0, grid_points)
    prior_weights = stats.norm.pdf(theta_grid, 0, 1)
    prior_weights /= np.sum(prior_weights)

    # Probabilities for correct (P) and incorrect (Q) responses
    P = compute_3pl_prob(theta_grid, a, b, c, D)  # (N_items, N_grid)
    log_P = np.log(P)
    log_Q = np.log(1.0 - P)

    # Calculate log-likelihood for each respondent: (N_students, N_grid)
    log_L = np.dot(X, log_P) + np.dot(1.0 - X, log_Q)

    # Log-sum-exp trick for numerical stability
    max_log_L = np.max(log_L, axis=1, keepdims=True)
    L = np.exp(log_L - max_log_L)

    # Posterior distribution
    posterior = L * prior_weights[None, :]  # (N_students, N_grid)
    posterior_sum = np.sum(posterior, axis=1, keepdims=True)
    posterior_norm = posterior / posterior_sum

    # EAP Estimate (Mean) and Standard Error
    theta_eap = np.sum(posterior_norm * theta_grid[None, :], axis=1)
    se_eap = np.sqrt(
        np.sum(posterior_norm * ((theta_grid[None, :] - theta_eap[:, None]) ** 2), axis=1)
    )

    return theta_eap, se_eap


# --- 5. Calculation & Output Display ---
st.divider()
st.subheader(f"Hasil Skoring ({len(matched_q_cols)} Soal Ter-match)")

with st.spinner("Menghitung skor IRT..."):
    if "EAP" in est_method:
        theta_estimates, se_estimates = score_eap(X, a, b, c, D)
    else:
        # Fallback MAP calculation using fine grid mode
        theta_grid = np.linspace(-4.0, 4.0, 161)
        P = compute_3pl_prob(theta_grid, a, b, c, D)
        log_L = np.dot(X, np.log(P)) + np.dot(1.0 - X, np.log(1.0 - P))
        log_prior = -0.5 * (theta_grid**2)
        log_posterior = log_L + log_prior
        best_indices = np.argmax(log_posterior, axis=1)
        theta_estimates = theta_grid[best_indices]
        se_estimates = np.zeros_like(theta_estimates)

results = []
for idx, row in df_resp.iterrows():
    test_taker = row[test_taker_col]
    if pd.isna(test_taker):
        continue

    cabang_val = row[cabang_col_name]
    raw_score = np.sum(X[idx])
    theta_val = theta_estimates[idx]
    se_val = se_estimates[idx]

    # Linear transformation formula
    scaled_score = np.clip(
        round(target_mean + target_sd * theta_val, 2), min_score, max_score
    )

    results.append(
        {
            "Nama": test_taker,
            "Cabang": cabang_val,
            "Banyak Soal Benar": int(raw_score),
            "Estimasi Theta": round(theta_val, 4),
            "Standard Error (SE)": round(se_val, 4) if "EAP" in est_method else "N/A",
            "Skor IRT": scaled_score,
        }
    )

df_results = pd.DataFrame(results).set_index("Nama")
st.dataframe(df_results, use_container_width=True)

# --- 6. Export Results ---
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    df_results.to_excel(writer, sheet_name="IRT_Results")

output_filename = f"{uploaded_file.name.rsplit('.', 1)[0]} IRT SKORING.xlsx"

st.download_button(
    label="Download Hasil Excel",
    data=buffer.getvalue(),
    file_name=output_filename,
)
