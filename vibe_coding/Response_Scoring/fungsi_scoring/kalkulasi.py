import io
import numpy as np
import pandas as pd
import scipy.stats as stats
import streamlit as st
from scipy.special import logsumexp

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
    """
    X = np.asarray(X, dtype=float)
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    c = np.asarray(c, dtype=float)

    if X.ndim != 2:
        raise ValueError("Matriks jawaban harus dua dimensi.")

    n_students, n_items = X.shape

    if n_students == 0 or n_items == 0:
        raise ValueError("Matriks jawaban tidak boleh kosong.")

    if not (len(a) == len(b) == len(c) == n_items):
        raise ValueError("Jumlah parameter tidak sama dengan jumlah soal.")

    if grid_points < 2:
        raise ValueError("grid_points minimal harus 2.")

    if not np.isfinite(X).all():
        raise ValueError("Matriks jawaban mengandung nilai tidak valid.")

    if not np.isin(X, [0, 1]).all():
        raise ValueError("Jawaban hanya boleh berupa 0 dan 1.")

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
            "Parameter IRT tidak valid. Pastikan a > 0, b bernilai finite, dan 0 <= c < 1."
        )

    theta_grid = np.linspace(-4.0, 4.0, grid_points)
    log_prior = stats.norm.logpdf(theta_grid, loc=0, scale=1)

    z = D * a[:, None] * (theta_grid[None, :] - b[:, None])
    logistic_prob = stats.logistic.cdf(z)
    P = c[:, None] + (1.0 - c[:, None]) * logistic_prob
    P = np.clip(P, 1e-12, 1.0 - 1e-12)

    log_P = np.log(P)
    log_Q = np.log1p(-P)

    log_L = X @ log_P + (1.0 - X) @ log_Q
    log_posterior = log_L + log_prior[None, :]

    log_normalizer = logsumexp(log_posterior, axis=1, keepdims=True)
    posterior = np.exp(log_posterior - log_normalizer)

    theta_eap = np.sum(posterior * theta_grid[None, :], axis=1)
    variance = np.sum(
        posterior * (theta_grid[None, :] - theta_eap[:, None]) ** 2,
        axis=1
    )
    se_eap = np.sqrt(np.maximum(variance, 0.0))

    return theta_eap, se_eap

def process_nilai(
    df_resp,
    subtest_configs,
    resp_id_map,
    raw_q_cols,
    test_taker_col,
    cabang_col_name,
    D,
    TARGET_MEAN,
    TARGET_SD,
    MIN_SCORE,
    MAX_SCORE
) -> pd.DataFrame:
    """
    Processes and calculates IRT 3PL scores across all configured parameter sets
    and returns a combined student results DataFrame.
    """
    valid_mask = df_resp[test_taker_col].notna() & df_resp[test_taker_col].astype(str).str.strip().ne("")
    df_results = pd.DataFrame({
        "Nama": df_resp.loc[valid_mask, test_taker_col],
        "Cabang": df_resp.loc[valid_mask, cabang_col_name]
    }).reset_index(drop=True)

    df_resp_valid = df_resp.loc[valid_mask].reset_index(drop=True)
    scoring_success = False

    for config in subtest_configs:
        label = config["label"]
        df_p = config["df_param"]
        param_id_set = set(df_p["Clean_ID"])

        matched_q_cols = [
            col for col in raw_q_cols if resp_id_map.get(col) in param_id_set
        ]

        if not matched_q_cols:
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

            scaled_scores = [
                np.clip(round(TARGET_MEAN + TARGET_SD * float(th), 2), MIN_SCORE, MAX_SCORE)
                for th in theta_estimates
            ]

            df_results[f"Jumlah Benar ({label})"] = raw_scores
            df_results[f"Theta ({label})"] = np.round(theta_estimates, 4)
            df_results[f"SE ({label})"] = np.round(se_estimates, 4)
            df_results[f"Skor IRT ({label})"] = scaled_scores

            scoring_success = True

        except Exception as e:
            st.error(f"Gagal menghitung skor untuk parameter {label}: {e}")

    if not scoring_success:
        return pd.DataFrame()

    return df_results