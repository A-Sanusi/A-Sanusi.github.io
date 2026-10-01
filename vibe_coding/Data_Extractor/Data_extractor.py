import io
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Ekstrak Data", layout="wide")
st.link_button("Menu", "https://a-sanusi.github.io/vibe_coding/vibe_coding.html")
st.title("Ekstrak Data")


def convert_df_to_excel(df: pd.DataFrame, sheet_name: str = "Sheet1") -> bytes:
    """Converts a DataFrame into an Excel file byte stream."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=True, sheet_name=sheet_name)
    return output.getvalue()


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
            "NAMA SISWA",
            "NAMA AKUN TO",
            "KELAS (DI PRIORITY)",
        ]
        if c in df_siswa.columns
    ]

    col_siswa_akun = next(
        (c for c in ["NAMA AKUN TO", "NAMA AKUN"] if c in df_siswa.columns),
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
                    for c in ["NAMA SISWA", "NAMA AKUN", "NAMA AKUN TO"]
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

    df_hasil = df_hasil.astype(object).fillna("-")
    df_hasil.index = range(1, len(df_hasil) + 1)
    df_hasil.index.name = "No"
    return df_hasil


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

    # RENAME HEADER FOR KEHADIRAN HERE
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
    """Calculates attendance percentage grouped by class, including an overall total summary."""
    df_calc = df_total.copy()

    hadir_cols = [
        c for c in df_calc.columns if c.startswith("TOTAL ") and "HADIR" in c
    ]
    izin_cols = [
        c for c in df_calc.columns if c.startswith("TOTAL ") and "IZIN" in c
    ]
    alpa_cols = [
        c for c in df_calc.columns if c.startswith("TOTAL ") and "ALPA" in c
    ]

    for col in hadir_cols + izin_cols + alpa_cols:
        df_calc[col] = pd.to_numeric(df_calc[col], errors="coerce").fillna(0)

    df_calc["_TOTAL_HADIR"] = df_calc[hadir_cols].sum(axis=1) if hadir_cols else 0
    df_calc["_TOTAL_IZIN"] = df_calc[izin_cols].sum(axis=1) if izin_cols else 0
    df_calc["_TOTAL_ALPA"] = df_calc[alpa_cols].sum(axis=1) if alpa_cols else 0
    df_calc["_TOTAL_PERTEMUAN"] = (
        df_calc["_TOTAL_HADIR"]
        + df_calc["_TOTAL_IZIN"]
        + df_calc["_TOTAL_ALPA"]
    )

    kelas_col = "KELAS" if "KELAS" in df_calc.columns else None

    if not kelas_col:
        return pd.DataFrame()

    df_kelas = (
        df_calc.groupby(kelas_col)
        .agg(
            Jumlah_Siswa=(
                ("NAMA SISWA", "count")
                if "NAMA SISWA" in df_calc.columns
                else (kelas_col, "count")
            ),
            Total_Hadir=("_TOTAL_HADIR", "sum"),
            Total_Izin=("_TOTAL_IZIN", "sum"),
            Total_Alpa=("_TOTAL_ALPA", "sum"),
            Total_Pertemuan=("_TOTAL_PERTEMUAN", "sum"),
        )
        .reset_index()
    )

    df_kelas["Persentase Kehadiran (%)"] = (
        (df_kelas["Total_Hadir"] / df_kelas["Total_Pertemuan"]) * 100
    ).round(2).fillna(0)

    # Calculate overall total across all classes
    tot_siswa = df_kelas["Jumlah_Siswa"].sum()
    tot_hadir = df_kelas["Total_Hadir"].sum()
    tot_izin = df_kelas["Total_Izin"].sum()
    tot_alpa = df_kelas["Total_Alpa"].sum()
    tot_pertemuan = df_kelas["Total_Pertemuan"].sum()
    tot_persen = round((tot_hadir / tot_pertemuan * 100), 2) if tot_pertemuan > 0 else 0.0

    total_row = pd.DataFrame([{
        kelas_col: "TOTAL SEMUA KELAS",
        "Jumlah_Siswa": tot_siswa,
        "Total_Hadir": tot_hadir,
        "Total_Izin": tot_izin,
        "Total_Alpa": tot_alpa,
        "Total_Pertemuan": tot_pertemuan,
        "Persentase Kehadiran (%)": tot_persen,
    }])

    df_kelas = pd.concat([df_kelas, total_row], ignore_index=True)

    df_kelas.index = range(1, len(df_kelas) + 1)
    df_kelas.index.name = "No"

    return df_kelas


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
        (c for c in ["NAMA AKUN BINSIK", "NAMA AKUN"] if c in df_siswa.columns),
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


# --- TAB LAYOUT ---
tab_db, tab_to_tka, tab_to_skd, tab_to_utbk, tab_kehadiran, tab_binsik = st.tabs([
    "🔴 Ekstrak Database",
    "🟣 Ekstrak Nilai TO TKA",
    "🔴 Ekstrak Nilai TO SKD (coming soon)",
    "🟣 Ekstrak Nilai TO UTBK (coming soon)",
    "🔴 Ekstrak Kehadiran",
    "🟣 Ekstrak Nilai Binsik",
])

# 1. DATABASE TAB
with tab_db:
    st.header("Ekstrak Database")
    uploaded_db = st.file_uploader(
        "Upload File Excel Database",
        type=["xlsx", "xls", "xlsm"],
        key="uploader_db",
    )

    if uploaded_db is None:
        st.info("Silakan upload file Excel Database untuk melanjutkan.")
    else:
        df_result = process_database(uploaded_db)
        st.dataframe(df_result, use_container_width=True)

        excel_bytes = convert_df_to_excel(df_result, sheet_name="Database")
        st.download_button(
            label="Download Database",
            data=excel_bytes,
            file_name="Database.xlsx",
            key="download_db",
        )

# 2. TO TKA TAB
with tab_to_tka:
    st.header("Nilai TO Kini ada Ekstraknya 🟣")

    col_to_tka_1, col_to_tka_2 = st.columns(2)
    with col_to_tka_1:
        uploaded_siswa = st.file_uploader(
            "Upload File Excel Nama Siswa",
            type=["xlsx", "xls", "xlsm"],
            key="uploader_to_siswa",
        )
    with col_to_tka_2:
        uploaded_to = st.file_uploader(
            "Upload File Try Out",
            type=["xlsx", "xls", "xlsm"],
            key="uploader_to_data",
        )

    if uploaded_siswa is None or uploaded_to is None:
        st.info("Silakan upload kedua file Excel untuk melanjutkan.")
    else:
        excel_siswa = pd.ExcelFile(uploaded_siswa)
        excel_to = pd.ExcelFile(uploaded_to)

        selected_sheet_siswa = st.selectbox(
            "Pilih Sheet Nama Siswa:",
            excel_siswa.sheet_names,
            key="sheet_siswa_select",
        )

        st.subheader("Pilih Sheet Subtes Try Out")
        target_subtests = st.multiselect(
            "Pilih Subtes yang Ingin Diekstrak:",
            options=excel_to.sheet_names,
            default=excel_to.sheet_names[: min(3, len(excel_to.sheet_names))],
            key="multiselect_subtests",
        )

        if not target_subtests:
            st.warning("Pilih minimal 1 subtes.")
        else:
            df_hasil = process_to_tka(
                uploaded_siswa, uploaded_to, selected_sheet_siswa, target_subtests
            )

            st.subheader("Tabel Nilai Siswa")
            st.dataframe(df_hasil, use_container_width=True)

            excel_bytes_to = convert_df_to_excel(
                df_hasil, sheet_name="Hasil Nilai TO"
            )
            st.download_button(
                label="Download Hasil Nilai",
                data=excel_bytes_to,
                file_name="Hasil_Nilai_Try_Out.xlsx",
                key="download_to",
            )

            st.divider()

            st.subheader("Rata-Rata Nilai per Kelas")

            score_cols = [
                col for col in df_hasil.columns if col.startswith("Nilai ")
            ]

            kelas_col = next(
                (
                    c
                    for c in ["KELAS (DI PRIORITY)"]
                    if c in df_hasil.columns
                ),
                None,
            )

            if score_cols and kelas_col:
                df_calc = df_hasil.copy()

                for col in score_cols:
                    df_calc[col] = pd.to_numeric(df_calc[col], errors="coerce")

                df_avg_kelas = (
                    df_calc.groupby(kelas_col)[score_cols].mean().round(2).reset_index()
                )
                df_avg_kelas.index = range(1, len(df_avg_kelas) + 1)
                df_avg_kelas.index.name = "No"

                st.dataframe(df_avg_kelas, use_container_width=True)

                fig = px.bar(
                    df_avg_kelas,
                    x=kelas_col,
                    y=score_cols,
                    barmode="group",
                    title="Rata-Rata Nilai Try Out per Kelas",
                    labels={
                        kelas_col: "Kelas",
                        "value": "Nilai Rata-Rata",
                        "variable": "Subtes TO",
                    },
                    text_auto=".2f",
                )

                fig.update_layout(
                    xaxis_title="Kelas",
                    yaxis_title="Nilai Rata-Rata",
                    margin=dict(l=20, r=20, t=50, b=20),
                )

                st.plotly_chart(fig, use_container_width=True)

                excel_bytes_avg = convert_df_to_excel(
                    df_avg_kelas, sheet_name="Rata-Rata per Kelas"
                )
                st.download_button(
                    label="Download Nilai Rata-Rata Kelas",
                    data=excel_bytes_avg,
                    file_name="Rata_Rata_Nilai_Per_Kelas.xlsx",
                    key="download_avg_kelas",
                )

# 3. TO SKD TAB
with tab_to_skd:
    st.header("Ekstrak Nilai SKD")
    st.info("Coming Soon")

# 4. TO UTBK TAB
with tab_to_utbk:
    st.header("Ekstrak Nilai UTBK")
    st.info("Coming Soon")

# 5. KEHADIRAN TAB
with tab_kehadiran:
    st.header("Ekstrak Kehadiran")
    uploaded_siswa_2 = st.file_uploader(
        "Upload File Excel Nama Siswa",
        type=["xlsx", "xls", "xlsm"],
        key="uploader_kehadiran_siswa",
    )

    if uploaded_siswa_2 is None:
        st.info("Silakan upload file Excel untuk melanjutkan.")
    else:
        excel_siswa_2 = pd.ExcelFile(uploaded_siswa_2)

        selected_sheet_siswa_2 = st.selectbox(
            "Pilih Sheet Data Siswa Utama:",
            excel_siswa_2.sheet_names,
            key="sheet_siswa_select_2",
        )

        selected_bulan = [
            "SEPTEMBER",
            "OKTOBER",
            "NOVEMBER",
            "DESEMBER",
            "JANUARI",
            "FEBRUARI",
            "MARET",
            "APRIL",
            "MEI",
            "JUNI",
            "JULI",
            "AGUSTUS",
        ]

        bulan_terpilih = st.selectbox(
            "Pilih Bulan Rapor", selected_bulan, key="bulan_kehadiran"
        )
        bulan_angka = selected_bulan.index(bulan_terpilih) + 1

        st.subheader("Pilih Sheet Kehadiran Tiap Bulan")
        cols = st.columns(min(bulan_angka, 4))
        selecting = {}

        for i in range(bulan_angka):
            col_idx = i % 4
            with cols[col_idx]:
                selecting[selected_bulan[i]] = st.selectbox(
                    f"Bulan {selected_bulan[i]}",
                    excel_siswa_2.sheet_names,
                    key=f"select_sheet_kehadiran{i}",
                )

        target_sheets = list(selecting.values())

        df_hasil_kehadiran = process_kehadiran(
            uploaded_siswa_2, selected_sheet_siswa_2, target_sheets
        )

        df_total_kehadiran = calculate_total_kehadiran(df_hasil_kehadiran)

        st.subheader("Rekap Kehadiran Siswa Per Bulan")
        st.dataframe(df_hasil_kehadiran, use_container_width=True)

        excel_bytes_kehadiran = convert_df_to_excel(
            df_hasil_kehadiran, sheet_name="Kehadiran Per Bulan"
        )
        st.download_button(
            label="Download Rekap Per Bulan",
            data=excel_bytes_kehadiran,
            file_name="Rekap_Kehadiran_Per_Bulan.xlsx",
            key="download_kehadiran_bulan",
        )

        st.divider()

        st.subheader("Rekap TOTAL Kehadiran Siswa")
        st.dataframe(df_total_kehadiran, use_container_width=True)

        excel_bytes_total = convert_df_to_excel(
            df_total_kehadiran, sheet_name="Total Kehadiran"
        )
        st.download_button(
            label="Download Rekap TOTAL",
            data=excel_bytes_total,
            file_name="Rekap_TOTAL_Kehadiran.xlsx",
            key="download_kehadiran_total",
        )

        # --- PERSENTASE KEHADIRAN PER KELAS ---
        st.divider()
        st.subheader("Persentase Kehadiran per Kelas")

        df_kehadiran_kelas = calculate_kehadiran_per_kelas(df_total_kehadiran)

        if not df_kehadiran_kelas.empty:
            # Display overall percentage total across all classes
            total_row = df_kehadiran_kelas[df_kehadiran_kelas["KELAS"] == "TOTAL SEMUA KELAS"]
            if not total_row.empty:
                overall_pct = total_row["Persentase Kehadiran (%)"].values[0]
                st.metric(
                    label="Total Persentase Kehadiran Semua Kelas",
                    value=f"{overall_pct:.2f}%",
                )

            st.dataframe(df_kehadiran_kelas, use_container_width=True)

            excel_bytes_kelas = convert_df_to_excel(
                df_kehadiran_kelas, sheet_name="Kehadiran per Kelas"
            )
            st.download_button(
                label="Download Persentase Kehadiran Kelas",
                data=excel_bytes_kelas,
                file_name="Persentase_Kehadiran_Per_Kelas.xlsx",
                key="download_kehadiran_kelas",
            )

# 6. BINSIK TAB
with tab_binsik:
    st.header("Ekstrak Nilai Binsik")

    col_binsik_1, col_binsik_2 = st.columns(2)
    with col_binsik_1:
        uploaded_siswa_3 = st.file_uploader(
            "Upload Excel Nama Siswa",
            type=["xlsx", "xls", "xlsm"],
            key="uploader_kehadiran_siswa_3",
        )

    with col_binsik_2:
        uploaded_binsik = st.file_uploader(
            "Upload File Binsik Siswa",
            type=["xlsx", "xls", "xlsm"],
            key="uploader_binsik",
        )

    if uploaded_siswa_3 is None or uploaded_binsik is None:
        st.info("Silakan upload kedua file Excel untuk melanjutkan.")
    else:
        excel_siswa_3 = pd.ExcelFile(uploaded_siswa_3)

        selected_sheet_siswa_3 = st.selectbox(
            "Pilih Sheet Data Siswa Utama:",
            excel_siswa_3.sheet_names,
            key="sheet_siswa_select_3",
        )

        excel_binsik = pd.ExcelFile(uploaded_binsik)

        selected_sheet_binsik = st.selectbox(
            "Pilih Data Binsik:", excel_binsik.sheet_names, key="sheet_binsik"
        )

        df_hasil_binsik = process_binsik(
            uploaded_siswa_3,
            uploaded_binsik,
            selected_sheet_siswa_3,
            selected_sheet_binsik,
        )

        st.subheader("Tabel Nilai Binsik Siswa")
        st.dataframe(df_hasil_binsik, use_container_width=True)

        excel_bytes_to = convert_df_to_excel(
            df_hasil_binsik, sheet_name="Hasil Nilai Binsik"
        )
        st.download_button(
            label="Download Hasil Nilai",
            data=excel_bytes_to,
            file_name="Hasil_Nilai_Binsik.xlsx",
            key="download_binsik",
        )
