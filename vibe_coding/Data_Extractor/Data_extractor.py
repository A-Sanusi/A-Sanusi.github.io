import io
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Ekstrak Data", layout="wide")
st.link_button("Menu", "https://a-sanusi.github.io/vibe_coding/vibe_coding.html")
st.title("Ekstrak Data")


def convert_df_to_excel(df, sheet_name="Sheet1"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=True, sheet_name=sheet_name)
    return output.getvalue()


def process_database(uploaded_file):
    df_siswa_raw = pd.read_excel(uploaded_file, sheet_name="DATA BASE")
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

    df_merged = df_siswa[selected_columns]
    df_merged.index = range(1, len(df_merged) + 1)
    df_merged.index.name = "No"
    df_merged = df_merged.astype(object).fillna("-")
    return df_merged


def process_to_tka(uploaded_siswa, uploaded_to, sheet_siswa, target_sheets):
    """Processes and merges Try Out scores with student data."""
    # 1. Load student list
    df_siswa_raw = pd.read_excel(
        uploaded_siswa, sheet_name=sheet_siswa, header=0
    )
    df_siswa = df_siswa_raw.dropna(how="all").copy()
    df_siswa.columns = df_siswa.columns.astype(str).str.strip()
    selected_siswa_cols = ["NAMA SISWA", "NAMA AKUN TO", "KELAS (DI PRIORITY)"]

    # Detect student account column dynamically
    col_siswa_akun = (
        "NAMA AKUN TO"
        if "NAMA AKUN TO" in df_siswa.columns
        else (
            "NAMA AKUN"
            if "NAMA AKUN" in df_siswa.columns
            else df_siswa.columns[1]
        )
    )

    df_siswa["key_match"] = (
        df_siswa[col_siswa_akun].astype(str).str.strip().str.lower()
    )

    # Keep requested student columns + key_match
    df_hasil = df_siswa[selected_siswa_cols + ["key_match"]].copy()

    # 2. Extract scores from chosen subtest sheets
    excel_to = pd.ExcelFile(uploaded_to)
    selected_to_cols = ["TOTAL BENAR", "NILAI", "KATEGORI"]

    for sheet in target_sheets:
        if sheet in excel_to.sheet_names:
            df_nilai_raw = pd.read_excel(
                uploaded_to, sheet_name=sheet, header=7
            ).dropna(how="all")

            df_nilai_raw.columns = df_nilai_raw.columns.astype(str).str.strip()

            # Detect account/name column in TO sheet ("NAMA SISWA", "NAMA AKUN", etc.)
            col_to_akun = next(
                (
                    c
                    for c in ["NAMA SISWA", "NAMA AKUN", "NAMA AKUN TO"]
                    if c in df_nilai_raw.columns
                ),
                df_nilai_raw.columns[1],
            )

            df_nilai_raw["key_match"] = (
                df_nilai_raw[col_to_akun]
                .astype(str)
                .str.strip()
                .str.lower()
            )

            # Filter present score columns
            available_score_cols = [
                c for c in selected_to_cols if c in df_nilai_raw.columns
            ]
            df_sub = (
                df_nilai_raw[["key_match"] + available_score_cols]
                .drop_duplicates(subset=["key_match"])
                .copy()
            )

            if "TOTAL BENAR" in df_sub.columns:
                df_sub["TOTAL BENAR"] = (
                    pd.to_numeric(df_sub["TOTAL BENAR"], errors="coerce")
                    .round()
                    .astype("Int64")
                )

            # Rename columns per subtest sheet
            rename_map = {
                "TOTAL BENAR": f"Jumlah_Nilai_Benar {sheet}",
                "NILAI": f"Nilai {sheet}",
                "KATEGORI": f"Kategori {sheet}",
            }
            df_sub = df_sub.rename(columns=rename_map)

            # Merge per subtest sheet
            df_hasil = pd.merge(df_hasil, df_sub, on="key_match", how="left")

    # 3. Clean final result DataFrame
    df_hasil = df_hasil.drop(columns=["key_match"]).dropna(
        subset=["NAMA SISWA"]
    )
    df_hasil = df_hasil.astype(object).fillna("-")
    df_hasil.index = range(1, len(df_hasil) + 1)
    df_hasil.index.name = "No"
    return df_hasil


def process_kehadiran(uploaded_file, sheet_siswa, target_sheets):
    # 1. Load base student list
    df_siswa_raw = pd.read_excel(
        uploaded_file, sheet_name=sheet_siswa, header=0
    )
    df_siswa = df_siswa_raw.dropna(how="all").copy()
    df_siswa.columns = df_siswa.columns.astype(str).str.strip()

    selected_siswa_cols = [
        c for c in ["NAMA SISWA"] if c in df_siswa.columns
    ]
    if not selected_siswa_cols:
        selected_siswa_cols = [df_siswa.columns[0]]

    # Detect student account column
    col_siswa_akun = next(
        (
            c
            for c in ["NAMA SISWA"]
            if c in df_siswa.columns
        ),
        df_siswa.columns[0],
    )

    df_siswa["key_match"] = (
        df_siswa[col_siswa_akun].astype(str).str.strip().str.lower()
    )
    df_hasil = df_siswa[selected_siswa_cols + ["key_match"]].copy()

    # Define target attendance headers to pull
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

    excel_file = pd.ExcelFile(uploaded_file)

    # 2. Extract existing columns sheet by sheet
    for sheet in target_sheets:
        if sheet in excel_file.sheet_names:
            df_sheet_raw = pd.read_excel(
                uploaded_file, sheet_name=sheet, header=0
            ).dropna(how="all")
            df_sheet_raw.columns = (
                df_sheet_raw.columns.astype(str).str.strip()
            )

            col_sheet_akun = next(
                (
                    c
                    for c in ["NAMA SISWA"]
                    if c in df_sheet_raw.columns
                ),
                df_sheet_raw.columns[0],
            )

            df_sheet_raw["key_match"] = (
                df_sheet_raw[col_sheet_akun]
                .astype(str)
                .str.strip()
                .str.lower()
            )

            # Filter present attendance columns
            avail_cols = [c for c in target_cols if c in df_sheet_raw.columns]
            df_sub = df_sheet_raw[["key_match"] + avail_cols].drop_duplicates(
                subset=["key_match"]
            )

            rename_map = {c: f"{c} ({sheet})" for c in avail_cols}
            df_sub = df_sub.rename(columns=rename_map)

            # Direct left merge
            df_hasil = pd.merge(df_hasil, df_sub, on="key_match", how="left")

    # 3. Clean up final result
    df_hasil = df_hasil.drop(columns=["key_match"]).dropna(
        subset=[selected_siswa_cols[0]]
    )
    df_hasil = df_hasil.fillna("0").astype(str)
    df_hasil.index = range(1, len(df_hasil) + 1)
    df_hasil.index.name = "No"

    return df_hasil


def calculate_total_kehadiran(df_monthly):
    """Calculates total attendance per student into a separate DataFrame."""
    col_siswa = (
        "NAMA SISWA"
        if "NAMA SISWA" in df_monthly.columns
        else df_monthly.columns[0]
    )
    df_total = pd.DataFrame({col_siswa: df_monthly[col_siswa]})

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
                .astype(str)
            )

    df_total.index = df_monthly.index
    df_total.index.name = "No"
    return df_total


def process_binsik(
    uploaded_siswa_3, uploaded_binsik, sheet_siswa, selected_sheet_binsik
):
    df_siswa_raw = pd.read_excel(uploaded_siswa_3, sheet_name=sheet_siswa)
    df_siswa = df_siswa_raw.dropna(how="all").copy()
    df_siswa.columns = df_siswa.columns.astype(str).str.strip()
    selected_siswa_cols = ["NAMA SISWA"]

    col_siswa_akun = (
        "NAMA AKUN BINSIK"
        if "NAMA AKUN BINSIK" in df_siswa.columns
        else (
            "NAMA AKUN"
            if "NAMA AKUN" in df_siswa.columns
            else df_siswa.columns[1]
        )
    )

    df_siswa["key_match"] = (
        df_siswa[col_siswa_akun].astype(str).str.strip().str.lower()
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

    df_nilai_raw = pd.read_excel(
        uploaded_binsik, sheet_name=selected_sheet_binsik, header=1
    ).dropna(how="all")

    df_nilai_raw.columns = df_nilai_raw.columns.astype(str).str.strip()

    col_to_akun = next(
        (c for c in ["NAMA SISWA"] if c in df_nilai_raw.columns),
        df_nilai_raw.columns[1],
    )

    df_nilai_raw["key_match"] = (
        df_nilai_raw[col_to_akun].astype(str).str.strip().str.lower()
    )

    available_score_cols = [
        c for c in selected_binsik_cols if c in df_nilai_raw.columns
    ]
    df_sub = (
        df_nilai_raw[["key_match"] + available_score_cols]
        .drop_duplicates(subset=["key_match"])
        .copy()
    )

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

    # --- ROUNDING LOGIC ---
    score_cols = [
        col for col in df_sub.columns if col.startswith("Total Skor")
    ]
    for col in score_cols:
        df_sub[col] = pd.to_numeric(df_sub[col], errors="coerce").round(2)

    # Merge per subtest sheet
    df_hasil = pd.merge(df_hasil, df_sub, on="key_match", how="left")

    # Final cleanup
    df_hasil = df_hasil.drop(columns=["key_match"]).dropna(
        subset=["NAMA SISWA"]
    )
    df_hasil = df_hasil.astype(object).fillna("-")
    df_hasil.index = range(1, len(df_hasil) + 1)
    df_hasil.index.name = "No"

    return df_hasil


tab_db, tab_to_tka, tab_to_skd, tab_to_utbk, tab_kehadiran, tab_binsik = (
    st.tabs(
        [
            "🔴 Ekstrak Database",
            "🟣 Ekstrak Nilai TO TKA",
            "🔴 Ekstrak Nilai TO SKD (coming soon)",
            "🟣 Ekstrak Nilai TO UTBK (coming soon)",
            "🔴 Ekstrak Kehadiran",
            "🟣 Ekstrak Nilai Binsik",
        ]
    )
)

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
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            s1 = st.selectbox("Subtes 1:", excel_to.sheet_names, key="s1")
        with col_s2:
            s2 = st.selectbox("Subtes 2:", excel_to.sheet_names, key="s2")
        with col_s3:
            s3 = st.selectbox("Subtes 3:", excel_to.sheet_names, key="s3")

        # 1. Process Student Scores
        df_hasil = process_to_tka(
            uploaded_siswa, uploaded_to, selected_sheet_siswa, [s1, s2, s3]
        )

        # 2. Display Individual Student Results
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

        # 3. Calculate & Display Average per KELAS
        st.subheader("Rata-Rata Nilai per Kelas")

        score_cols = [
            col for col in df_hasil.columns if col.startswith("Nilai ")
        ]

        if score_cols:
            df_calc = df_hasil.copy()

            # Safely parse numeric score values
            for col in score_cols:
                df_calc[col] = pd.to_numeric(df_calc[col], errors="coerce")

            cols_to_avg = score_cols

            df_avg_kelas = (
                df_calc.groupby("KELAS (DI PRIORITY)")[cols_to_avg]
                .mean()
                .round(2)
                .reset_index()
            )
            df_avg_kelas.index = range(1, len(df_avg_kelas) + 1)
            df_avg_kelas.index.name = "No"

            st.dataframe(df_avg_kelas, use_container_width=True)

            # --- PLOTLY EXPRESS BAR CHART ---
            fig = px.bar(
                df_avg_kelas,
                x="KELAS (DI PRIORITY)",
                y=cols_to_avg,
                barmode="group",
                title="Rata-Rata Nilai Try Out per Kelas",
                labels={
                    "KELAS (DI PRIORITY)": "Kelas",
                    "value": "Nilai Rata-Rata",
                    "variable": "Subtes / Kategori",
                },
                text_auto=".2f",
            )

            fig.update_layout(
                xaxis_title="Kelas",
                yaxis_title="Nilai Rata-Rata",
                legend_title="Kategori",
                hovermode="x unified",
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

with tab_to_skd:
    st.header("Ekstrak Nilai SKD")
    st.info("Coming Soon")

with tab_to_utbk:
    st.header("Ekstrak Nilai UTBK")
    st.info("Coming Soon")

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

        # Generate Monthly DataFrame
        df_hasil_kehadiran = process_kehadiran(
            uploaded_siswa_2, selected_sheet_siswa_2, target_sheets
        )

        # Generate Total DataFrame separately
        df_total_kehadiran = calculate_total_kehadiran(df_hasil_kehadiran)

        # --- TABLE 1: Monthly Breakdown ---
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

        # --- TABLE 2: Total Summary ---
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
