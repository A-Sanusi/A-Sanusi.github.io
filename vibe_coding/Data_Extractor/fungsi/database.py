import pandas as pd

def process_database(uploaded_file) -> pd.DataFrame:
    """Processes the database excel sheet and returns extracted student records."""
    excel_file = pd.ExcelFile(uploaded_file)

    target_sheet = next(
        (s for s in excel_file.sheet_names if s.strip().upper() == "DATA BASE"),
        excel_file.sheet_names[0],
    )

    df_siswa_raw = excel_file.parse(sheet_name=target_sheet)
    df_siswa = df_siswa_raw.dropna(how="all").copy()
    df_siswa.columns = df_siswa.columns.astype(str).str.strip()

    selected_columns = [
        "NAMA SISWA",
        "NAMA AKUN TO",
        "ASAL SEKOLAH",
        "JURUSAN",
        "PROGRAM BELAJAR",
        "KELAS (DI PRIORITY)",
        "MINAT PTN",
        "MINAT SEKOLAH KEDINASAN",
    ]

    available_cols = [c for c in selected_columns if c in df_siswa.columns]
    df_merged = df_siswa[available_cols].copy()

    df_merged.index = range(1, len(df_merged) + 1)
    df_merged.index.name = "No"
    df_merged = df_merged.astype(object).fillna("-")
    return df_merged