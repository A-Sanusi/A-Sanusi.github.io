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