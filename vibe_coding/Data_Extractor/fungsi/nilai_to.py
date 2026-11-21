import pandas as pd

def process_to_tka(
    uploaded_siswa, uploaded_to, sheet_siswa: str, target_sheets: list[str]
) -> pd.DataFrame:
    """Processes and merges Try Out scores with student data."""
    excel_siswa = pd.ExcelFile(uploaded_siswa)
    excel_to = pd.ExcelFile(uploaded_to)

    df_siswa_raw = excel_siswa.parse(sheet_name=sheet_siswa, header=0)
    df_siswa = df_siswa_raw.dropna(how="all").copy()
    df_siswa.columns = df_siswa.columns.astype(str).str.strip()

    selected_siswa_cols = [
        c
        for c in [
            "NAMA AKUN TO",
            "NAMA SISWA",
            "KELAS (DI PRIORITY)",
        ]
        if c in df_siswa.columns
    ]

    col_siswa_akun = next(
        (c for c in ["NAMA AKUN TO", "NAMA SISWA"] if c in df_siswa.columns),
        df_siswa.columns[1] if len(df_siswa.columns) > 1 else df_siswa.columns[0],
    )

    df_siswa["key_match"] = (
        df_siswa[col_siswa_akun].fillna("").astype(str).str.strip().str.lower()
    )

    df_hasil = df_siswa[selected_siswa_cols + ["key_match"]].copy()

    selected_to_cols = ["TOTAL BENAR", "NILAI", "KATEGORI"]

    for sheet in target_sheets:
        if sheet in excel_to.sheet_names:
            df_nilai_raw = excel_to.parse(sheet_name=sheet, header=7).dropna(
                how="all"
            )
            df_nilai_raw.columns = df_nilai_raw.columns.astype(str).str.strip()

            col_to_akun = next(
                (
                    c
                    for c in ["NAMA AKUN TO", "NAMA SISWA"]
                    if c in df_nilai_raw.columns
                ),
                df_nilai_raw.columns[1]
                if len(df_nilai_raw.columns) > 1
                else df_nilai_raw.columns[0],
            )

            df_nilai_raw["key_match"] = (
                df_nilai_raw[col_to_akun]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.lower()
            )

            available_score_cols = [
                c for c in selected_to_cols if c in df_nilai_raw.columns
            ]
            df_sub = df_nilai_raw[["key_match"] + available_score_cols].drop_duplicates(
                subset=["key_match"]
            ).copy()

            if "TOTAL BENAR" in df_sub.columns:
                df_sub["TOTAL BENAR"] = (
                    pd.to_numeric(df_sub["TOTAL BENAR"], errors="coerce")
                    .round()
                    .astype("Int64")
                )

            if "NILAI" in df_sub.columns:
                df_sub["NILAI"] = pd.to_numeric(df_sub["NILAI"], errors="coerce")

            rename_map = {
                "TOTAL BENAR": f"Jumlah_Nilai_Benar {sheet}",
                "NILAI": f"Nilai {sheet}",
                "KATEGORI": f"Kategori {sheet}",
            }
            df_sub = df_sub.rename(columns=rename_map)

            df_hasil = pd.merge(df_hasil, df_sub, on="key_match", how="left")

    df_hasil = df_hasil.drop(columns=["key_match"])
    if "NAMA SISWA" in df_hasil.columns:
        df_hasil = df_hasil.dropna(subset=["NAMA SISWA"])

    # Handle missing values safely without converting numbers to object/dates
    for col in df_hasil.columns:
        if any(prefix in col for prefix in ["Nilai", "Jumlah_Nilai_Benar"]):
            df_hasil[col] = pd.to_numeric(df_hasil[col], errors="coerce")
        else:
            df_hasil[col] = df_hasil[col].astype(object).fillna("-")

    df_hasil.index = range(1, len(df_hasil) + 1)
    df_hasil.index.name = "No"
    return df_hasil

def process_postes(
    uploaded_siswa, uploaded_to_list: list, sheet_siswa: str, target_sheets: list[str]
) -> pd.DataFrame:
    """Processes and merges Try Out scores from multiple Excel files with student data."""
    excel_siswa = pd.ExcelFile(uploaded_siswa)
    excel_files_to = [pd.ExcelFile(f) for f in uploaded_to_list]

    df_siswa_raw = excel_siswa.parse(sheet_name=sheet_siswa, header=0)
    df_siswa = df_siswa_raw.dropna(how="all").copy()
    df_siswa.columns = df_siswa.columns.astype(str).str.strip()

    selected_siswa_cols = [
        c
        for c in [
            "NAMA AKUN TO",
            "NAMA SISWA",
            "KELAS (DI PRIORITY)",
        ]
        if c in df_siswa.columns
    ]

    col_siswa_akun = next(
        (c for c in ["NAMA AKUN TO", "NAMA SISWA"] if c in df_siswa.columns),
        df_siswa.columns[1] if len(df_siswa.columns) > 1 else df_siswa.columns[0],
    )

    df_siswa["key_match"] = (
        df_siswa[col_siswa_akun].fillna("").astype(str).str.strip().str.lower()
    )

    df_hasil = df_siswa[selected_siswa_cols + ["key_match"]].copy()
    selected_to_cols = ["NILAI"]

    # Iterate through each target subtest sheet
    for sheet in target_sheets:
        sheet_dfs = []

        # Check every uploaded file for this sheet
        for excel_to in excel_files_to:
            if sheet in excel_to.sheet_names:
                df_nilai_raw = excel_to.parse(sheet_name=sheet, header=0).dropna(
                    how="all"
                )
                df_nilai_raw.columns = df_nilai_raw.columns.astype(str).str.strip()

                col_to_akun = next(
                    (
                        c
                        for c in ["NAMA AKUN TO", "NAMA SISWA"]
                        if c in df_nilai_raw.columns
                    ),
                    df_nilai_raw.columns[1]
                    if len(df_nilai_raw.columns) > 1
                    else df_nilai_raw.columns[0],
                )

                df_nilai_raw["key_match"] = (
                    df_nilai_raw[col_to_akun]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                    .str.lower()
                )

                available_score_cols = [
                    c for c in selected_to_cols if c in df_nilai_raw.columns
                ]
                df_sub = df_nilai_raw[["key_match"] + available_score_cols].copy()

                if "NILAI" in df_sub.columns:
                    df_sub["NILAI"] = pd.to_numeric(df_sub["NILAI"], errors="coerce")

                sheet_dfs.append(df_sub)

        # Combine rows if the same sheet existed across multiple uploaded files
        if sheet_dfs:
            df_combined_sheet = pd.concat(sheet_dfs, ignore_index=True).drop_duplicates(
                subset=["key_match"]
            )
            
            # Use "Nilai {sheet}" so score_cols_postes and numeric casting work properly
            col_name = sheet if sheet.startswith("Nilai ") else f"Nilai {sheet}"
            df_combined_sheet = df_combined_sheet.rename(columns={"NILAI": col_name})

            df_hasil = pd.merge(df_hasil, df_combined_sheet, on="key_match", how="left")

    df_hasil = df_hasil.drop(columns=["key_match"])
    if "NAMA SISWA" in df_hasil.columns:
        df_hasil = df_hasil.dropna(subset=["NAMA SISWA"])

    # Handle missing values safely without converting numbers to object/dates
    for col in df_hasil.columns:
        if any(prefix in col for prefix in ["Nilai", "Jumlah_Nilai_Benar"]):
            df_hasil[col] = pd.to_numeric(df_hasil[col], errors="coerce")
        else:
            df_hasil[col] = df_hasil[col].astype(object).fillna("-")

    df_hasil.index = range(1, len(df_hasil) + 1)
    df_hasil.index.name = "No"
    return df_hasil

def process_to(
    uploaded_siswa, uploaded_to, sheet_siswa: str, target_sheets: list[str]
) -> pd.DataFrame:
    """Processes and merges Try Out scores with student data."""
    excel_siswa = pd.ExcelFile(uploaded_siswa)
    excel_to = pd.ExcelFile(uploaded_to)

    df_siswa_raw = excel_siswa.parse(sheet_name=sheet_siswa, header=0)
    df_siswa = df_siswa_raw.dropna(how="all").copy()
    df_siswa.columns = df_siswa.columns.astype(str).str.strip().str.upper()

    selected_siswa_cols = [
        c
        for c in [
            "NAMA AKUN TO",
            "NAMA SISWA",
            "KELAS (DI PRIORITY)",
        ]
        if c in df_siswa.columns
    ]

    col_siswa_akun = next(
        (c for c in ["NAMA AKUN TO", "NAMA SISWA"] if c in df_siswa.columns),
        df_siswa.columns[1] if len(df_siswa.columns) > 1 else df_siswa.columns[0],
    )

    df_siswa["key_match"] = (
        df_siswa[col_siswa_akun].fillna("").astype(str).str.strip().str.lower()
    )

    df_hasil = df_siswa[selected_siswa_cols + ["key_match"]].copy()

    numeric_cols_created = []

    for sheet in target_sheets:
        if sheet in excel_to.sheet_names:
            df_nilai_raw = excel_to.parse(sheet_name=sheet, header=7).dropna(
                how="all"
            )
            df_nilai_raw.columns = (
                df_nilai_raw.columns.astype(str)
                .str.replace(r"\s+", " ", regex=True)
                .str.strip()
                .str.upper()
            )

            col_to_akun = next(
                (
                    c
                    for c in ["NAMA AKUN TO", "NAMA SISWA"]
                    if c in df_nilai_raw.columns
                ),
                df_nilai_raw.columns[1]
                if len(df_nilai_raw.columns) > 1
                else df_nilai_raw.columns[0],
            )

            df_nilai_raw["key_match"] = (
                df_nilai_raw[col_to_akun]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.lower()
            )

            # Must use df_nilai_raw.columns INSIDE the loop (not df_siswa_raw)
            available_score_cols = (
                [c for c in df_nilai_raw.columns if c.startswith("TOTAL")]
                + [c for c in df_nilai_raw.columns if c.startswith("NILAI")]
                + [c for c in ["KATEGORI", "RATA-RATA", "RANK"] if c in df_nilai_raw.columns]
            )

            df_sub = df_nilai_raw[["key_match"] + available_score_cols].drop_duplicates(
                subset=["key_match"]
            ).copy()

            # Dynamically rename columns to include the sheet name (e.g., "NILAI PU (Testing)")
            rename_map = {}
            for col in available_score_cols:
                new_name = f"{col} ({sheet})"
                rename_map[col] = new_name
                numeric_cols_created.append(new_name)

                # Format 'TOTAL BENAR' columns as integers, others as numeric
                if col == "KATEGORI":
                    # Keep as text and clean whitespace
                    df_sub[col] = df_sub[col].astype(str).str.strip().replace("nan", pd.NA)
                elif "TOTAL BENAR" in col:
                    df_sub[col] = (
                        pd.to_numeric(df_sub[col], errors="coerce")
                        .round()
                        .astype("Int64")
                    )
                else:
                    df_sub[col] = pd.to_numeric(df_sub[col], errors="coerce")

            df_sub = df_sub.rename(columns=rename_map)
            df_hasil = pd.merge(df_hasil, df_sub, on="key_match", how="left")

    df_hasil = df_hasil.drop(columns=["key_match"])
    if "NAMA SISWA" in df_hasil.columns:
        df_hasil = df_hasil.dropna(subset=["NAMA SISWA"])

    # Handle missing values safely
    for col in df_hasil.columns:
        if col not in numeric_cols_created:
            df_hasil[col] = df_hasil[col].astype(object).fillna("-")

    df_hasil.index = range(1, len(df_hasil) + 1)
    df_hasil.index.name = "No"
    return df_hasil