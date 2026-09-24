import io
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
import streamlit as st

st.set_page_config(page_title="Skoring IRT 3PL", layout="wide")
st.title("Skoring IRT (3PL Model)")


def clean_question_id(series_or_columns):
    """Clean and normalize item IDs for robust matching."""
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
        "1. Upload Jawaban Siswa (Biner: 1/0)", type=["xlsx", "xls", "xlsm"]
    )

with col2:
    uploaded_file_2 = st.file_uploader(
        "2. Upload Parameter Try Out", type=["xlsx", "xls", "xlsm"]
    )

if uploaded_file is None or uploaded_file_2 is None:
    st.info("Silakan upload kedua file Excel.")
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

# Identify question columns (skipping metadata columns)
raw_q_cols = df_resp.columns[3:]

# --- 3. Load & Clean Parameter Sheet ---
excel_file_2 = pd.ExcelFile(uploaded_file_2)
selected_sheet_2 = st.selectbox(
    "Pilih Sheet Parameter:", excel_file_2.sheet_names, key="sheet_param"
)
df_param_raw = pd.read_excel(uploaded_file_2, sheet_name=selected_sheet_2)

# Column mapping: expecting Discrimination (a), Difficulty (b), Guessing (c)
df_param = df_param_raw.iloc[:, [2, 3, 4, 5, 6]].copy()
df_param.columns = ["Nomor Soal", "Question ID", "Discrimination", "Difficulty", "Guessing"]
df_param["Clean_ID"] = clean_question_id(df_param["Question ID"])

# Build ID mapping for response columns
resp_q_ids = clean_question_id(raw_q_cols)
resp_id_map = dict(zip(raw_q_cols, resp_q_ids))

# Match item parameters by Clean_ID
matched_q_cols = [col for col in raw_q_cols if resp_id_map[col] in set(df_param["Clean_ID"])]

if not matched_q_cols:
    st.error("Tidak ada Question ID yang cocok antara sheet jawaban dan sheet parameter.")
    st.stop()

df_param_indexed = df_param.set_index("Clean_ID")
matched_param_ids = [resp_id_map[col] for col in matched_q_cols]

df_param_aligned = df_param_indexed.loc[matched_param_ids]

# Extract 3PL parameters
a = pd.to_numeric(df_param_aligned["Discrimination"], errors="coerce").values
b = pd.to_numeric(df_param_aligned["Difficulty"], errors="coerce").values
c = pd.to_numeric(df_param_aligned["Guessing"], errors="coerce").values

# Prepare binary response matrix
df_resp_aligned = (
    df_resp[matched_q_cols]
    .astype(str)
    .apply(lambda col: col.str.strip())
    .apply(pd.to_numeric, errors="coerce")
    .fillna(0)
)


# --- 4. 3PL IRT Functions (MAP Estimation) ---
def probability_3pl(theta, a, b, c, D=1.0):
    """3PL Logistic Response Function."""
    return c + (1.0 - c) / (1.0 + np.exp(-D * a * (theta - b)))


def negative_log_posterior(theta, response, a, b, c):
    """
    Negative Log Posterior (MAP with Normal N(0,1) Prior)
    Prevents divergence for extreme scores and scores <= guessing level.
    """
    p = probability_3pl(theta, a, b, c)
    p = np.clip(p, 1e-9, 1.0 - 1e-9)

    # Log-Likelihood
    ll = np.sum(response * np.log(p) + (1.0 - response) * np.log(1.0 - p))

    # Log-Prior: standard normal N(0, 1) -> -0.5 * theta^2
    log_prior = -0.5 * (theta**2)

    return -(ll + log_prior)


def estimate_ability_map(response, a, b, c):
    """Coarse grid search followed by bounded scalar optimization."""
    grid_thetas = np.linspace(-4.0, 4.0, 81)
    grid_nlp = [negative_log_posterior(t, response, a, b, c) for t in grid_thetas]
    best_grid_theta = grid_thetas[np.argmin(grid_nlp)]

    lower_b = max(-4.0, best_grid_theta - 1.5)
    upper_b = min(4.0, best_grid_theta + 1.5)

    result = minimize_scalar(
        negative_log_posterior,
        bounds=(lower_b, upper_b),
        args=(response, a, b, c),
        method="bounded",
    )
    return result.x


# --- 5. Execution & Results Display ---
st.divider()
st.subheader(f"Hasil Skoring (Matched Items: {len(matched_q_cols)})")

results = []
for idx, row in df_resp.iterrows():
    test_taker = row[test_taker_col]
    if pd.isna(test_taker):
        continue

    cabang_val = row[cabang_col_name]
    response_vector = df_resp_aligned.loc[idx].values
    raw_score = np.sum(response_vector)

    # Maximum A Posteriori Ability Estimation
    theta_est = estimate_ability_map(response_vector, a, b, c)
    skor_irt = np.clip(round(500 + 75 * theta_est, 2), 200, 800)

    results.append(
        {
            "Nama": test_taker,
            "Cabang": cabang_val,
            "Banyak Soal Benar": int(raw_score),
            "Estimasi Theta": round(theta_est, 4),
            "Skor IRT": skor_irt,
        }
    )

df_results = pd.DataFrame(results).set_index("Nama")
st.dataframe(df_results, use_container_width=True)

# --- 6. Export to Excel ---
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    df_results.to_excel(writer, sheet_name="3PL_IRT_Results")

output_filename = f"{uploaded_file.name.rsplit('.', 1)[0]} IRT SKORING.xlsx"

st.download_button(
    label="Download Hasil Excel",
    data=buffer.getvalue(),
    file_name=output_filename,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
