import io
import numpy as np
import pandas as pd
import scipy.stats as stats
import streamlit as st

st.set_page_config(page_title="Skoring IRT 3PL", layout="wide")
st.link_button("Menu", "https://a-sanusi.github.io/vibe_coding/vibe_coding.html")
st.title("Skoring IRT")

D = 1.702
TARGET_MEAN = 500.0
TARGET_SD = 75.0
MIN_SCORE = 200.0
MAX_SCORE = 800.0

def clean_question_id(series_or_columns):
    """Normalize Question IDs for robust matching."""
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
        "1. Upload Jawaban Siswa", type=["xlsx", "xls", "xlsm"]
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

# Match response columns with parameter rows via Question ID
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

# Prepare binary response matrix
X = (
    df_resp[matched_q_cols]
    .astype(str)
    .apply(lambda col: col.str.strip())
    .apply(pd.to_numeric, errors="coerce")
    .fillna(0)
    .values
)

# --- 4. Vectorized 3PL EAP Scoring Function ---
def score_eap_3pl(X, a, b, c, D=1.702, grid_points=101):
    theta_grid = np.linspace(-4.0, 4.0, grid_points)
    prior_weights = stats.norm.pdf(theta_grid, 0, 1)
    prior_weights /= np.sum(prior_weights)

    # Calculate item response probabilities (N_items, N_grid)
    exp_term = np.exp(-D * a[:, None] * (theta_grid[None, :] - b[:, None]))
    P = c[:, None] + (1.0 - c[:, None]) / (1.0 + exp_term)
    P = np.clip(P, 1e-9, 1.0 - 1e-9)

    log_P = np.log(P)
    log_Q = np.log(1.0 - P)

    # Log-Likelihood per respondent (N_students, N_grid)
    log_L = np.dot(X, log_P) + np.dot(1.0 - X, log_Q)

    # Log-sum-exp trick for numerical precision
    max_log_L = np.max(log_L, axis=1, keepdims=True)
    L = np.exp(log_L - max_log_L)

    # Normalize posterior distribution
    posterior = L * prior_weights[None, :]
    posterior_norm = posterior / np.sum(posterior, axis=1, keepdims=True)

    # Expectation (Mean) and Variance (SE)
    theta_eap = np.sum(posterior_norm * theta_grid[None, :], axis=1)
    se_eap = np.sqrt(
        np.sum(posterior_norm * ((theta_grid[None, :] - theta_eap[:, None]) ** 2), axis=1)
    )
    return theta_eap, se_eap

# --- 5. Calculation & Display ---
st.divider()
st.subheader(f"Hasil Skoring")

with st.spinner("Menghitung skor IRT EAP..."):
    theta_estimates, se_estimates = score_eap_3pl(X, a, b, c, D)

results = []
for idx, row in df_resp.iterrows():
    test_taker = row[test_taker_col]
    if pd.isna(test_taker):
        continue

    cabang_val = row[cabang_col_name]
    raw_score = np.sum(X[idx])
    theta_val = theta_estimates[idx]

    scaled_score = np.clip(
        round(TARGET_MEAN + TARGET_SD * theta_val, 2), MIN_SCORE, MAX_SCORE
    )

    results.append(
        {
            "Nama": test_taker,
            "Cabang": cabang_val,
            "Banyak Soal Benar": int(raw_score),
            "Estimasi Theta": round(theta_val, 4),
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
