import io
import re
import zipfile
import pandas as pd
import numpy as np
import streamlit as st
from scipy.optimize import minimize

# Must be the first Streamlit command in the script
st.set_page_config(page_title="Penilaian")
st.title("IRT Tools")

# 1. Dynamic File Upload Widget
uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx", "xls", "xlsm"])

# 2. Halt execution until a file is uploaded
if uploaded_file is None:
    st.stop()

# 3. Inspect available sheets dynamically
excel_file = pd.ExcelFile(uploaded_file)
sheet_names = excel_file.sheet_names
selected_sheet = st.selectbox("Select Sheet:", sheet_names, index=0)

# Read the uploaded file and selected sheet
df = pd.read_excel(uploaded_file, sheet_name=selected_sheet)

# Select items (From index 3 to the last column)
total_cols = df.shape[1]
df_items = df.iloc[:, 0:total_cols].copy()
df_items = df_items.apply(pd.to_numeric, errors='coerce').fillna(0).astype(int)

# Filter out non-varying columns (std == 0)
valid_cols = [col for col in df_items.columns if df_items[col].std() > 0]
clean_items = df_items[valid_cols]

# Response matrix X of shape (N_students, J_items)
X = clean_items.values
N, J = X.shape

#Fungsi
def sigmoid(z):
    return 1 / (1 + np.exp(-np.clip(z, -30, 30)))

# Joint Log-Likelihood with priors to stabilize estimation
def neg_log_likelihood(params, X, N, J):
    theta = params[:N]
    a = params[N : N + J]
    b = params[N + J :]
    
    # P_ij = P(X_ij = 1 | theta_i, a_j, b_j)
    Z = a[None, :] * (theta[:, None] - b[None, :])
    P = sigmoid(Z)
    P = np.clip(P, 1e-9, 1 - 1e-9)
    
    # Bernoulli log-likelihood
    log_lik = np.sum(X * np.log(P) + (1 - X) * np.log(1 - P))
    
    # Normal priors to prevent extreme drift (Bayesian Regularization)
    prior_theta = np.sum(-0.5 * (theta ** 2))
    prior_a = np.sum(-0.5 * ((a - 1.0) ** 2))
    prior_b = np.sum(-0.5 * (b ** 2))
    
    return -(log_lik + prior_theta + prior_a + prior_b)

#Parameterisasi
with st.spinner("Loading..."):
    # Initial guesses: theta = standardized raw score, a = 1, b = inverted difficulty
    raw_totals = X.sum(axis=1)
    init_theta = (raw_totals - raw_totals.mean()) / (raw_totals.std() + 1e-5)
    init_a = np.ones(J)
    init_b = -np.log((X.mean(axis=0) + 1e-3) / (1 - X.mean(axis=0) + 1e-3))

    init_params = np.concatenate([init_theta, init_a, init_b])

    # Bounds: a (discrimination) [0.01, 4.0], b (difficulty) [-4.0, 4.0]
    bounds = (
        [(None, None)] * N +
        [(0.01, 4.0)] * J +
        [(-4.0, 4.0)] * J
    )

    res = minimize(
        neg_log_likelihood, 
        init_params, 
        args=(X, N, J), 
        method='L-BFGS-B', 
        bounds=bounds,
        options={'maxiter': 500}
    )

    # Extract estimated theta scores
    estimated_theta = res.x[:N]

    # Standardize theta to Mean = 0, SD = 1
    estimated_theta = (estimated_theta - estimated_theta.mean()) / (estimated_theta.std() + 1e-5)

#Skoring
df['Benar'] = df_items.sum(axis=1)
df['Theta'] = estimated_theta
df['Skor'] = (500 + (df['Theta'] * 100)).clip(200, 800).round(2)

#Output
output_buffer = io.BytesIO()
with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
    df.to_excel(writer, index=False)
output_buffer.seek(0)

st.download_button(
    label="Download Skoring (.xlsx)",
    data=output_buffer,
    file_name=f"Processed_{uploaded_file.name}",
)
