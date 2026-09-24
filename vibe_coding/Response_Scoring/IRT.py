import io
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
import streamlit as st

st.set_page_config(page_title="3PL IRT Model Calculator", layout="wide")
st.title("3PL Item Response Theory (IRT) Calculator")


# --- Helper Function for ID Standardization ---
def clean_question_id(series_or_columns):
    """Standardizes IDs across datasets by removing prefixes, trailing floats, and whitespace."""
    return (
        series_or_columns.astype(str)
        .str.replace(r"^ID\s*:\s*", "", regex=True)  # Remove 'ID:' prefix
        .str.replace(
            r"\.0$", "", regex=True
        )  # Remove trailing .0 from float conversions
        .str.strip()
    )


# --- 1. File Uploaders ---
col1, col2 = st.columns(2)

with col1:
    uploaded_file = st.file_uploader(
        "1. Upload Responses Excel", type=["xlsx", "xls", "xlsm"]
    )

with col2:
    uploaded_file_2 = st.file_uploader(
        "2. Upload Parameters Excel", type=["xlsx", "xls", "xlsm"]
    )

if uploaded_file is None or uploaded_file_2 is None:
    st.info("Silakan upload file.")
    st.stop()

# --- 2. Load Responses Sheet ---
excel_file = pd.ExcelFile(uploaded_file)
selected_sheet = st.selectbox(
    "Select Responses Sheet:", excel_file.sheet_names, key="sheet_resp"
)
df_resp_raw = pd.read_excel(uploaded_file, sheet_name=selected_sheet, header=1)
df_resp = df_resp_raw.iloc[1:].copy()

# Store column references BEFORE setting index
test_taker_col = df_resp.columns[0]
cabang_col_name = df_resp.columns[1]  # Store column name for Cabang (Column B)

df_resp.set_index(test_taker_col, inplace=True)
df_resp.dropna(how="all", inplace=True)

# Clean question headers
df_resp.columns = clean_question_id(df_resp.columns)

# --- 3. Load Parameters Sheet ---
excel_file_2 = pd.ExcelFile(uploaded_file_2)
selected_sheet_2 = st.selectbox(
    "Select Parameters Sheet:", excel_file_2.sheet_names, key="sheet_param"
)
df_param_raw = pd.read_excel(uploaded_file_2, sheet_name=selected_sheet_2)
df_param = df_param_raw.iloc[:, [3, 4, 5, 6]].copy()
df_param.columns = ["Question ID", "Discrimination", "Difficulty", "Guessing"]
df_param["Question ID"] = clean_question_id(df_param["Question ID"])
df_param = df_param.drop_duplicates(subset=["Question ID"])

# --- 4. Align Parameters with Response Columns ---
common_questions = [
    q for q in df_resp.columns if q in df_param["Question ID"].values
]

if not common_questions:
    st.error(
        "Gagal! No matching Question IDs found between Responses and Parameters."
    )
    st.stop()

df_param_aligned = df_param.set_index("Question ID").loc[common_questions]
df_resp_aligned = df_resp[common_questions].apply(
    pd.to_numeric, errors="coerce"
).fillna(0)

a = df_param_aligned["Discrimination"].values
b = df_param_aligned["Difficulty"].values
c = df_param_aligned["Guessing"].values


# --- 5. 3PL IRT Mathematical Functions ---
def probability_3pl(theta, a, b, c):
    return c + (1 - c) / (1 + np.exp(-a * (theta - b)))


def negative_log_likelihood(theta, response, a, b, c):
    p = probability_3pl(theta, a, b, c)
    p = np.clip(p, 1e-9, 1 - 1e-9)
    ll = np.sum(response * np.log(p) + (1 - response) * np.log(1 - p))
    return -ll


def estimate_ability(response, a, b, c):
    result = minimize_scalar(
        negative_log_likelihood,
        bounds=(-4.0, 4.0),
        args=(response, a, b, c),
        method="bounded",
    )
    return result.x


# --- 6. Execution & Results Display ---
st.divider()
st.subheader("Results")

results = []
for test_taker, row in df_resp_aligned.iterrows():
    response_vector = row.values

    # ✅ Extract actual cell value for Cabang for this test taker row
    cabang_val = df_resp.loc[test_taker, clean_question_id(pd.Series([cabang_col_name]))[0]]
    if isinstance(cabang_val, pd.Series):
        cabang_val = cabang_val.iloc[0]

    raw_score = np.sum(response_vector)
    theta_est = estimate_ability(response_vector, a, b, c)
    skor_irt = np.clip(round(500 + 75 * theta_est, 2), 200, 800)

    results.append({
        "Nama": test_taker,
        "Cabang": cabang_val,
        "Banyak Soal Benar": int(raw_score),
        "Estimasi Parameter": round(theta_est, 4),
        "Skor IRT": skor_irt,
    })

df_results = pd.DataFrame(results).set_index("Nama")

st.write(
    f"Successfully processed **{len(df_results)}** test takers across"
    f" **{len(common_questions)}** items."
)
st.dataframe(df_results, use_container_width=True)

# --- 7. Export to Excel ---
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    df_results.to_excel(writer, sheet_name="3PL_IRT_Results")

output_filename = f"{uploaded_file.name.rsplit('.', 1)[0]} IRT SKORING.xlsx"

st.download_button(
    label="Download Hasil",
    data=buffer.getvalue(),
    file_name=output_filename,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
