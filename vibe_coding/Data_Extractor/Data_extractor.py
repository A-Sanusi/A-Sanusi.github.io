import io
import pandas as pd
import streamlit as st

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
    selected_siswa_cols = ["NAMA SISWA", "NAMA AKUN TO"]

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

            col_to_akun = next(
                (c for c in ["NAMA SISWA"] if c in df_nilai_raw.columns),
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
            df_sub = df_nilai_raw[
                ["key_match"] + available_score_cols
            ].drop_duplicates(subset=["key_match"]).copy()

            if "TOTAL BENAR" in df_sub.columns:
                df_sub["TOTAL BENAR"] = (
                    pd.to_numeric(df_sub["TOTAL BENAR"], errors="coerce")
                    .round()
                    .astype("Int64")
                )

            # Rename columns per subtest sheet
            rename_map = {
                "TOTAL BENAR": f"Jumlah_Nilai_Benar_{sheet}",
                "NILAI": f"Nilai_{sheet}",
                "KATEGORI": f"Kategori_{sheet}",
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

    return df_hasil


def read_excel_smart_attendance(uploaded_file, sheet_name):
    """Detects header placement, combines 2-row multi-headers (e.g., Row 1: KBM | BINSIK,

    Row 2: HADIR | IZIN | ALPA or H | I | A), and forward-fills merged cells.
    """
    df_raw = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=None)

    # 1. Find the header row by searching for student name keywords
    header_idx = None
    for i, row in df_raw.iterrows():
        row_str = " ".join([str(v).upper() for v in row.values if pd.notna(v)])
        if "NAMA" in row_str or "SISWA" in row_str:
            header_idx = i
            break

    if header_idx is None:
        header_idx = 0

    # 2. Check if the row below contains sub-headers
    is_multi_header = False
    if header_idx + 1 < len(df_raw):
        next_row_vals = [
            str(v).strip().upper()
            for v in df_raw.iloc[header_idx + 1].values
            if pd.notna(v)
        ]
        is_multi_header = any(
            sub in next_row_vals
            for sub in ["HADIR", "IZIN", "ALPA", "H", "I", "A", "SAKIT", "S"]
        )

    if is_multi_header:
        # Row 1 (Category: KBM, BINSIK) — forward-fill merged columns
        cat_row = (
            df_raw.iloc[header_idx]
            .ffill()
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        # Row 2 (Status: HADIR, IZIN, ALPA or H, I, A)
        stat_row = (
            df_raw.iloc[header_idx + 1]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        # Translate single letter codes if used in Excel
        code_map = {"H": "HADIR", "I": "IZIN", "A": "ALPA", "S": "SAKIT"}

        combined_headers = []
        for cat, stat in zip(cat_row, stat_row):
            cat_clean = (
                "" if "UNNAMED" in cat or cat in ["NAN", "NONE"] else cat
            )
            stat_clean = (
                "" if "UNNAMED" in stat or stat in ["NAN", "NONE"] else stat
            )
            stat_clean = code_map.get(stat_clean, stat_clean)

            if cat_clean and stat_clean and stat_clean not in cat_clean:
                combined_headers.append(f"{cat_clean} {stat_clean}")
            elif cat_clean:
                combined_headers.append(cat_clean)
            elif stat_clean:
                combined_headers.append(stat_clean)
            else:
                combined_headers.append("UNKNOWN")

        df_data = df_raw.iloc[header_idx + 2 :].copy()
        df_data.columns = combined_headers
    else:
        # Single header row setup
        df_data = pd.read_excel(
            uploaded_file, sheet_name=sheet_name, header=header_idx
        )
        df_data.columns = [
            str(c).replace("\xa0", " ").strip().upper()
            for c in df_data.columns
        ]

    return df_data.dropna(how="all")


def process_kehadiran(uploaded_file, sheet_siswa, target_sheets):
    """Processes attendance with 2-row header support, name normalization, and numeric conversion."""
    # 1. Load base student list
    df_siswa = read_excel_smart_attendance(uploaded_file, sheet_siswa)

    possible_name_cols = ["NAMA SISWA", "NAMA AKUN TO", "NAMA AKUN", "NAMA"]
    col_siswa_akun = next(
        (c for c in possible_name_cols if c in df_siswa.columns),
        df_siswa.columns[0],
    )

    selected_siswa_cols = [
        c for c in ["NAMA SISWA", "NAMA AKUN TO"] if c in df_siswa.columns
    ]
    if not selected_siswa_cols:
        selected_siswa_cols = [col_siswa_akun]

    df_siswa["key_match"] = (
        df_siswa[col_siswa_akun]
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
        .str.lower()
    )
    df_hasil = df_siswa[selected_siswa_cols + ["key_match"]].copy()

    target_cols = [
        "KBM HADIR",
        "KBM IZIN",
        "KBM ALPA",
        "BINSIK HADIR",
        "BINSIK IZIN",
        "BINSIK ALPA",
    ]

    excel_file = pd.ExcelFile(uploaded_file)

    # 2. Extract existing columns sheet by sheet
    for sheet in target_sheets:
        if sheet in excel_file.sheet_names:
            df_sheet = read_excel_smart_attendance(uploaded_file, sheet)

            col_sheet_akun = next(
                (c for c in possible_name_cols if c in df_sheet.columns),
                df_sheet.columns[0],
            )

            df_sheet["key_match"] = (
                df_sheet[col_sheet_akun]
                .astype(str)
                .str.replace(r"\s+", " ", regex=True)
                .str.strip()
                .str.lower()
            )

            # Match target columns flexibly
            matched_cols_map = {}
            for target in target_cols:
                for col in df_sheet.columns:
                    if col.strip().upper() == target.upper():
                        matched_cols_map[col] = f"{target} ({sheet})"
                        break

            if matched_cols_map:
                sub_cols = ["key_match"] + list(matched_cols_map.keys())
                df_sub = df_sheet[sub_cols].drop_duplicates(
                    subset=["key_match"]
                ).copy()

                # Safely convert extracted attendance values to integer numbers
                for orig_col in matched_cols_map.keys():
                    df_sub[orig_col] = (
                        pd.to_numeric(df_sub[orig_col], errors="coerce")
                        .fillna(0)
                        .astype(int)
                    )

                df_sub = df_sub.rename(columns=matched_cols_map)
                df_hasil = pd.merge(
                    df_hasil, df_sub, on="key_match", how="left"
                )

    # 3. Clean up final result
    df_hasil = df_hasil.drop(columns=["key_match"]).dropna(
        subset=[selected_siswa_cols[0]]
    )
    df_hasil = df_hasil.fillna(0)
    df_hasil.index = range(1, len(df_hasil) + 1)

    return df_hasil


# --- NAVIGATION TABS ---
tab_db, tab_to_tka, tab_to_skd, tab_to_utbk, tab_kehadiran, tab_binsik = (
    st.tabs(
        [
            "🔴 Ekstrak Database",
            "🟣 Ekstrak Nilai TO TKA",
            "🔴 Ekstrak Nilai TO SKD (coming soon)",
            "🟣 Ekstrak Nilai TO UTBK (coming soon)",
            "🔴 Ekstrak Kehadiran",
            "🟣 Ekstrak Nilai Binsik (coming soon)",
        ]
    )
)

# Tab_database
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

# Tab_TKA
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

        df_hasil = process_to_tka(
            uploaded_siswa, uploaded_to, selected_sheet_siswa, [s1, s2, s3]
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

with tab_to_skd:
    st.header("Ekstrak Nilai SKD")
    st.info("Coming Soon")

with tab_to_utbk:
    st.header("Ekstrak Nilai UTBK")
    st.info("Coming Soon")

with tab_kehadiran:
    st.header("Ekstrak Kehadiran")
    uploaded_siswa_2 = st.file_uploader(
        "Upload File Excel Nama Siswa / Kehadiran",
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

        # Select sheets for each month
        st.subheader("Pilih Sheet Kehadiran Tiap Bulan")
        cols = st.columns(
            min(bulan_angka, 4)
        )  # Grid layout max 4 cols per row
        selecting = {}

        for i in range(bulan_angka):
            col_idx = i % 4
            with cols[col_idx]:
                selecting[selected_bulan[i]] = st.selectbox(
                    f"Bulan {selected_bulan[i]}",
                    excel_siswa_2.sheet_names,
                    key=f"select_sheet_kehadiran_{i}",
                )

        target_sheets = list(selecting.values())

        # Process execution outside the selection loop
        df_hasil_kehadiran = process_kehadiran(
            uploaded_siswa_2, selected_sheet_siswa_2, target_sheets
        )

        st.subheader("Tabel Rekap Kehadiran Siswa")
        st.dataframe(df_hasil_kehadiran, use_container_width=True)

        excel_bytes_kehadiran = convert_df_to_excel(
            df_hasil_kehadiran, sheet_name="Hasil Kehadiran"
        )
        st.download_button(
            label="Download Rekap Kehadiran",
            data=excel_bytes_kehadiran,
            file_name="Rekap_Kehadiran_Siswa.xlsx",
            key="download_kehadiran",
        )

with tab_binsik:
    st.header("Ekstrak Nilai Binsik")
    st.info("Coming Soon")
