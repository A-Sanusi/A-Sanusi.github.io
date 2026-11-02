import pandas as pd

def process_kehadiran(
    uploaded_file, sheet_siswa: str, target_sheets: list[str]
) -> pd.DataFrame:
    """Processes attendance sheets and merges attendance stats per student."""
    excel_file = pd.ExcelFile(uploaded_file)

    # 1. Load base student list
    df_siswa_raw = excel_file.parse(sheet_name=sheet_siswa, header=0)
    df_siswa = df_siswa_raw.dropna(how="all").copy()
    df_siswa.columns = df_siswa.columns.astype(str).str.strip()

    selected_siswa_cols = [
        c
        for c in [
            "NAMA SISWA",
            "KELAS (DI PRIORITY)",
        ]
        if c in df_siswa.columns
    ]
    if not selected_siswa_cols:
        selected_siswa_cols = [df_siswa.columns[0]]

    col_siswa_akun = next(
        (c for c in ["NAMA SISWA"] if c in df_siswa.columns),
        df_siswa.columns[0],
    )

    df_siswa["key_match"] = (
        df_siswa[col_siswa_akun].fillna("").astype(str).str.strip().str.lower()
    )
    df_hasil = df_siswa[selected_siswa_cols + ["key_match"]].copy()

    # Rename class header for consistency
    df_hasil = df_hasil.rename(columns={"KELAS (DI PRIORITY)": "KELAS"})

    # Target attendance headers
    target_cols = [
        "KBM HADIR",
        "BINSIK HADIR",
        "TO HADIR",
        "KBM IZIN",
        "BINSIK IZIN",
        "TO IZIN",
        "KBM ALPA",
        "BINSIK ALPA",
        "TO ALPA",
    ]

    # 2. Extract existing columns sheet by sheet using parsed excel_file
    for sheet in target_sheets:
        if sheet in excel_file.sheet_names:
            df_sheet_raw = excel_file.parse(sheet_name=sheet, header=0).dropna(
                how="all"
            )
            df_sheet_raw.columns = df_sheet_raw.columns.astype(str).str.strip()

            col_sheet_akun = next(
                (c for c in ["NAMA SISWA"] if c in df_sheet_raw.columns),
                df_sheet_raw.columns[0],
            )

            df_sheet_raw["key_match"] = (
                df_sheet_raw[col_sheet_akun]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.lower()
            )

            avail_cols = [c for c in target_cols if c in df_sheet_raw.columns]
            df_sub = df_sheet_raw[["key_match"] + avail_cols].drop_duplicates(
                subset=["key_match"]
            )

            rename_map = {c: f"{c} ({sheet})" for c in avail_cols}
            df_sub = df_sub.rename(columns=rename_map)

            df_hasil = pd.merge(df_hasil, df_sub, on="key_match", how="left")

    # 3. Clean up final result
    first_col = selected_siswa_cols[0]
    if first_col in df_hasil.columns:
        df_hasil = df_hasil.dropna(subset=[first_col])

    df_hasil = df_hasil.drop(columns=["key_match"])
    df_hasil = df_hasil.fillna("0").astype(str)
    df_hasil.index = range(1, len(df_hasil) + 1)
    df_hasil.index.name = "No"

    return df_hasil

def calculate_total_kehadiran(df_monthly: pd.DataFrame) -> pd.DataFrame:
    """Calculates total attendance metrics per student into a summary DataFrame."""
    target_metrics = [
        "KBM HADIR",
        "BINSIK HADIR",
        "TO HADIR",
        "KBM IZIN",
        "BINSIK IZIN",
        "TO IZIN",
        "KBM ALPA",
        "BINSIK ALPA",
        "TO ALPA",
    ]

    info_cols = [
        col
        for col in df_monthly.columns
        if not any(col.startswith(f"{m} (") for m in target_metrics)
    ]

    df_total = df_monthly[info_cols].copy()

    for metric in target_metrics:
        matching_cols = [
            col for col in df_monthly.columns if col.startswith(f"{metric} (")
        ]
        if matching_cols:
            df_total[f"TOTAL {metric}"] = (
                df_monthly[matching_cols]
                .apply(pd.to_numeric, errors="coerce")
                .fillna(0)
                .sum(axis=1)
                .astype(int)
            )

    df_total.index = df_monthly.index
    df_total.index.name = "No"
    return df_total

def calculate_kehadiran_per_kelas(df_total: pd.DataFrame) -> pd.DataFrame:
    """Calculates total attendance amounts and % HADIR grouped by class, including an overall total summary."""
    df_calc = df_total.copy()

    categories = ["KBM", "BINSIK", "TO"]
    statuses = ["HADIR", "IZIN", "ALPA"]
    df_cols = set(df_calc.columns)

    # 1. Identify valid columns and ensure they are numeric
    target_cols = []
    for cat in categories:
        for status in statuses:
            header = f"TOTAL {cat} {status}"
            if header in df_cols:
                target_cols.append(header)
                df_calc[header] = pd.to_numeric(df_calc[header], errors="coerce").fillna(0)

    kelas_col = "KELAS" if "KELAS" in df_calc.columns else None

    if not kelas_col or not target_cols:
        return pd.DataFrame()

    # 2. Group by KELAS and calculate sum of amounts
    df_summary = df_calc.groupby(kelas_col, as_index=False)[target_cols].sum()

    # 3. Calculate grand totals across all classes
    grand_total = df_summary[target_cols].sum().to_frame().T
    grand_total[kelas_col] = "TOTAL"

    # 4. Combine class totals with grand total
    result_df = pd.concat([df_summary, grand_total], ignore_index=True)

    # 5. Add Percentage HADIR columns (% HADIR KBM, % HADIR BINSIK, % HADIR TO)
    for cat in categories:
        hadir_col = f"TOTAL {cat} HADIR"
        izin_col = f"TOTAL {cat} IZIN"
        alpa_col = f"TOTAL {cat} ALPA"

        if hadir_col in result_df.columns:
            total_cat = 0
            for col in [hadir_col, izin_col, alpa_col]:
                if col in result_df.columns:
                    total_cat += result_df[col]

            pct_col = f"% HADIR {cat}"
            result_df[pct_col] = (
                (result_df[hadir_col] / total_cat * 100)
                .fillna(0)
                .round(2)
                .astype(str) + "%"
            )

    result_df.index = range(1, len(result_df) + 1)
    result_df.index.name = "No"

    return result_df