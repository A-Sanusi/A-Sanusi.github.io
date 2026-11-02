import pandas as pd

def process_binsik(
    uploaded_siswa_3,
    uploaded_binsik,
    sheet_siswa: str,
    selected_sheet_binsik: str,
) -> pd.DataFrame:
    """Processes physical fitness test (Binsik) scores."""
    excel_siswa = pd.ExcelFile(uploaded_siswa_3)
    excel_binsik = pd.ExcelFile(uploaded_binsik)

    df_siswa_raw = excel_siswa.parse(sheet_name=sheet_siswa)
    df_siswa = df_siswa_raw.dropna(how="all").copy()
    df_siswa.columns = df_siswa.columns.astype(str).str.strip()
    selected_siswa_cols = [
        c for c in ["NAMA SISWA"] if c in df_siswa.columns
    ] or [df_siswa.columns[0]]

    col_siswa_akun = next(
        (c for c in ["NAMA AKUN", "NAMA AKUN BINSIK"] if c in df_siswa.columns),
        df_siswa.columns[1] if len(df_siswa.columns) > 1 else df_siswa.columns[0],
    )

    df_siswa["key_match"] = (
        df_siswa[col_siswa_akun].fillna("").astype(str).str.strip().str.lower()
    )
    df_hasil = df_siswa[selected_siswa_cols + ["key_match"]].copy()

    selected_binsik_cols = [
        "JUMLAH LARI",
        "JUMLAH SHUTTLE RUN",
        "JUMLAH PUSH UP",
        "JUMLAH SIT UP",
        "JUMLAH PULL UP",
        "JUMLAH CHINNING UP",
        "NILAI LARI",
        "NILAI SHUTTLE RUN",
        "NILAI PUSH UP",
        "NILAI SIT UP",
        "NILAI PULL UP",
        "NILAI CHINNING UP",
        "T-SCORE",
        "KELULUSAN",
    ]

    df_nilai_raw = excel_binsik.parse(
        sheet_name=selected_sheet_binsik, header=1
    ).dropna(how="all")
    df_nilai_raw.columns = df_nilai_raw.columns.astype(str).str.strip()

    col_to_akun = next(
        (c for c in ["NAMA SISWA"] if c in df_nilai_raw.columns),
        df_nilai_raw.columns[1]
        if len(df_nilai_raw.columns) > 1
        else df_nilai_raw.columns[0],
    )

    df_nilai_raw["key_match"] = (
        df_nilai_raw[col_to_akun].fillna("").astype(str).str.strip().str.lower()
    )

    available_score_cols = [
        c for c in selected_binsik_cols if c in df_nilai_raw.columns
    ]
    df_sub = df_nilai_raw[["key_match"] + available_score_cols].drop_duplicates(
        subset=["key_match"]
    ).copy()

    rename_map = {
        "JUMLAH LARI": f"Jumlah Lari {selected_sheet_binsik}",
        "JUMLAH SHUTTLE RUN": f"Shuttle Run {selected_sheet_binsik}",
        "JUMLAH PUSH UP": f"Push Up {selected_sheet_binsik}",
        "JUMLAH SIT UP": f"Jumlah Sit Up {selected_sheet_binsik}",
        "JUMLAH PULL UP": f"Jumlah Pull Up {selected_sheet_binsik}",
        "JUMLAH CHINNING UP": f"Jumlah Chinning Up {selected_sheet_binsik}",
        "NILAI LARI": f"Nilai Lari {selected_sheet_binsik}",
        "NILAI SHUTTLE RUN": f"Nilai Shuttle Run {selected_sheet_binsik}",
        "NILAI PUSH UP": f"Nilai Push Up {selected_sheet_binsik}",
        "NILAI SIT UP": f"Nilai Sit Up {selected_sheet_binsik}",
        "NILAI PULL UP": f"Nilai Pull Up {selected_sheet_binsik}",
        "NILAI CHINNING UP": f"Nilai Chinning Up {selected_sheet_binsik}",
        "T-SCORE": f"Total Skor {selected_sheet_binsik}",
        "KELULUSAN": f"Kelulusan {selected_sheet_binsik}",
    }
    df_sub = df_sub.rename(columns=rename_map)

    score_cols = [col for col in df_sub.columns if col.startswith("Total Skor")]
    for col in score_cols:
        df_sub[col] = pd.to_numeric(df_sub[col], errors="coerce").round(2)

    df_hasil = pd.merge(df_hasil, df_sub, on="key_match", how="left")

    df_hasil = df_hasil.drop(columns=["key_match"])
    if selected_siswa_cols[0] in df_hasil.columns:
        df_hasil = df_hasil.dropna(subset=[selected_siswa_cols[0]])

    df_hasil = df_hasil.astype(object).fillna("-")
    df_hasil.index = range(1, len(df_hasil) + 1)
    df_hasil.index.name = "No"

    return df_hasil