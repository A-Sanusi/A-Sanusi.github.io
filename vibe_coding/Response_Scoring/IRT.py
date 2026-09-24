import io
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
import streamlit as st

st.set_page_config(page_title="Skoring IRT", layout="wide")
st.title("Skoring IRT")


def clean_question_id(series_or_columns):
    return (
        series_or_columns.astype(str)
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
    st.info("Silakan upload file.")
    st.stop()

# --- 2. Load Responses Sheet ---
excel_file = pd.ExcelFile(uploaded_file)
selected_sheet = st.selectbox(
    "Pilih Sheet Jawaban:", excel_file.sheet_names, key="sheet_resp"
)

# Read response data (header on row 1, skipping total column if present)
df_resp_raw = pd.read_excel(uploaded_file, sheet_name=selected_sheet, header=1)
df_resp = df_resp_raw.dropna(how="all").copy()

# Store metadata columns
test_taker_col = df_resp.columns[0]
cabang_col_name = df_resp.columns[1]

# Identify question columns (starting from index 3 to skip Name, Cabang, Total)
question_cols = df_resp.columns[3:]

# --- 3. Load Parameters Sheet ---
excel_file_2 = pd.ExcelFile(uploaded_file_2)
selected_sheet_2 = st.selectbox(
    "Pilih Sheet Parameter:", excel_file_2.sheet_names, key="sheet_param"
)
df_param_raw = pd.read_excel(uploaded_file_2, sheet_name=selected_sheet_2)

# Ensure parameters are sorted by question number / positional order
df_param = df_param_raw.iloc[:, [2, 3, 4, 5, 6]].copy()
df_param.columns = ["Nomor Soal", "Question ID", "Discrimination", "Difficulty", "Guessing"]
df_param["Question ID"] = clean_question_id(df_param["Question ID"])

# Match by position or Question ID
n_items = min(len(question_cols), len(df_param))
aligned_q_cols = question_cols[:n_items]
df_param_aligned = df_param.iloc[:n_items]

# Clean response data matrix
df_resp_aligned = (
    df_resp[aligned_q_cols]
    .astype(str)
    .apply(lambda col: col.str.strip())
    .apply(pd.to_numeric, errors="coerce")
    .fillna(0)
)

a = df_param_aligned["Discrimination"].values
b = df_param_aligned["Difficulty"].values
c = df_param_aligned["Guessing"].values


# --- 4. 3PL IRT Mathematical Functions ---
def probability_3pl(theta, a, b, c):
    return c + (1 - c) / (1 + np.exp(-a * (theta - b)))


def negative_log_likelihood(theta, response, a, b, c):
    p = probability_3pl(theta, a, b, c)
    p = np.clip(p, 1e-9, 1 - 1e-9)
    ll = np.sum(response * np.log(p) + (1 - response) * np.log(1 - p))
    return -ll


def estimate_ability(response, a, b, c):
    # Coarse grid search to prevent local minima traps
    grid_thetas = np.linspace(-4.0, 4.0, 81)
    grid_nll = [negative_log_likelihood(t, response, a, b, c) for t in grid_thetas]
    best_grid_theta = grid_thetas[np.argmin(grid_nll)]

    # Bounded optimization centered around best grid point
    lower_b = max(-4.0, best_grid_theta - 1.0)
    upper_b = min(4.0, best_grid_theta + 1.0)

    result = minimize_scalar(
        negative_log_likelihood,
        bounds=(lower_b, upper_b),
        args=(response, a, b, c),
        method="bounded",
    )
    return result.x


# --- 5. Execution & Results Display ---
st.divider()
st.subheader("Hasil")

results = []
for idx, row in df_resp.iterrows():
    test_taker = row[test_taker_col]
    if pd.isna(test_taker):
        continue

    cabang_val = row[cabang_col_name]
    response_vector = df_resp_aligned.loc[idx].values
    raw_score = np.sum(response_vector)

    theta_est = estimate_ability(response_vector, a, b, c)
    skor_irt = np.clip(round(500 + 75 * theta_est, 2), 200, 800)

    results.append({
        "Nama": test_taker,
        "Cabang": cabang_val,
        "Banyak Soal Benar": int(raw_score),
        "Estimasi Theta": round(theta_est, 4),
        "Skor IRT": skor_irt,
    })

df_results = pd.DataFrame(results).set_index("Nama")
st.dataframe(df_results, use_container_width=True)

# --- 6. Export to Excel ---
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    df_results.to_excel(writer, sheet_name="3PL_IRT_Results")

output_filename = f"{uploaded_file.name.rsplit('.', 1)[0]} IRT SKORING.xlsx"

st.download_button(
    label="Download Hasil",
    data=buffer.getvalue(),
    file_name=output_filename,
)
