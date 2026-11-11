import io
import pandas as pd
import plotly.express as px
import streamlit as st
from fungsi.binsik import process_binsik
from fungsi.database import process_database
from fungsi.excel_exporter import convert_df_to_excel
from fungsi.kehadiran import (
    calculate_kehadiran_per_kelas,
    calculate_total_kehadiran,
    process_kehadiran,
)
from fungsi.nilai_to import (
    process_to_tka,
    process_to_utbk,
    process_postes,
)

st.set_page_config(page_title="Ekstrak Data", layout="wide")
st.link_button("Menu", "https://a-sanusi.github.io/vibe_coding/vibe_coding.html")
st.title("Ekstrak Data")

# --- TAB LAYOUT ---
tab_db, tab_to_tka, tab_to_skd, tab_to_utbk, tab_kehadiran, tab_binsik, tab_postes = st.tabs([
    "🔴 Ekstrak Database",
    "🟣 Ekstrak Nilai TO TKA",
    "🔴 Ekstrak Nilai TO SKD (coming soon)",
    "🟣 Ekstrak Nilai TO UTBK (coming soon)",
    "🔴 Ekstrak Kehadiran",
    "🟣 Ekstrak Nilai Binsik",
    "🔴 Ekstrak Nilai Postes",
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
            default=excel_to.sheet_names[: min(0, len(excel_to.sheet_names))],
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

    col_to_utbk_1, col_to_utbk_2 = st.columns(2)
    with col_to_utbk_1:
        uploaded_siswa_utbk = st.file_uploader(
            "Upload File Excel Nama Siswa",
            type=["xlsx", "xls", "xlsm"],
            key="uploader_to_siswa_utbk",
        )
    with col_to_utbk_2:
        uploaded_to_utbk = st.file_uploader(
            "Upload File Try Out",
            type=["xlsx", "xls", "xlsm"],
            key="uploader_to_data_utbk",
        )

    if uploaded_siswa_utbk is None or uploaded_to_utbk is None:
        st.info("Silakan upload kedua file Excel untuk melanjutkan.")
    else:
        excel_siswa_utbk = pd.ExcelFile(uploaded_siswa_utbk)
        excel_to_utbk = pd.ExcelFile(uploaded_to_utbk)

        selected_sheet_siswa_utbk = st.selectbox(
            "Pilih Sheet Nama Siswa:",
            excel_siswa_utbk.sheet_names,
            key="sheet_siswa_select_utbk",
        )

        st.subheader("Pilih Sheet Subtes Try Out")
        target_subtests_utbk = st.multiselect(
            "Pilih Subtes yang Ingin Diekstrak:",
            options=excel_to_utbk.sheet_names,
            default=excel_to_utbk.sheet_names[: min(0, len(excel_to_utbk.sheet_names))],
            key="multiselect_subtests_utbk",
        )

        if not target_subtests_utbk:
            st.warning("Pilih minimal 1 subtes.")
        else:
            df_hasil_utbk = process_to_utbk(
                uploaded_siswa_utbk, uploaded_to_utbk, selected_sheet_siswa_utbk, target_subtests_utbk
            )

            st.subheader("Tabel Nilai Siswa")
            st.dataframe(df_hasil_utbk, use_container_width=True)

            excel_bytes_to_utbk = convert_df_to_excel(
                df_hasil_utbk, sheet_name="Hasil Nilai TO"
            )
            st.download_button(
                label="Download Hasil Nilai",
                data=excel_bytes_to_utbk,
                file_name="Hasil_Nilai_Try_Out_UTBK.xlsx",
                key="download_to_utbk",
            )

            st.divider()

            st.subheader("Rata-Rata Nilai per Kelas")

            score_cols_utbk = [
                col for col in df_hasil_utbk.columns if col.startswith("Nilai ")
            ]

            kelas_col_utbk = next(
                (
                    c
                    for c in ["KELAS (DI PRIORITY)"]
                    if c in df_hasil_utbk.columns
                ),
                None,
            )

            if score_cols_utbk and kelas_col_utbk:
                df_calc_utbk = df_hasil_utbk.copy()

                for col in score_cols_utbk:
                    df_calc_utbk[col] = pd.to_numeric(df_calc_utbk[col], errors="coerce")

                df_avg_kelas_utbk = (
                    df_calc_utbk.groupby(kelas_col_utbk)[score_cols_utbk].mean().round(2).reset_index()
                )
                df_avg_kelas_utbk.index = range(1, len(df_avg_kelas_utbk) + 1)
                df_avg_kelas_utbk.index.name = "No"

                st.dataframe(df_avg_kelas_utbk, use_container_width=True)

                fig_utbk = px.bar(
                    df_avg_kelas_utbk,
                    x=kelas_col_utbk,
                    y=score_cols_utbk,
                    barmode="group",
                    title="Rata-Rata Nilai Try Out per Kelas",
                    labels={
                        kelas_col_utbk: "Kelas",
                        "value": "Nilai Rata-Rata",
                        "variable": "Subtes TO",
                    },
                    text_auto=".2f",
                )

                fig_utbk.update_layout(
                    xaxis_title="Kelas",
                    yaxis_title="Nilai Rata-Rata",
                    margin=dict(l=20, r=20, t=50, b=20),
                )

                st.plotly_chart(fig_utbk, use_container_width=True)

                excel_bytes_avg_utbk = convert_df_to_excel(
                    df_avg_kelas_utbk, sheet_name="Rata-Rata per Kelas"
                )
                st.download_button(
                    label="Download Nilai Rata-Rata Kelas",
                    data=excel_bytes_avg,
                    file_name="Rata_Rata_Nilai_Per_Kelas.xlsx",
                    key="download_avg_kelas",
                )

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

        # --- REKAP KEHADIRAN PER KELAS ---
        st.divider()
        st.subheader("Rekap Kehadiran per Kelas")

        df_kehadiran_kelas = calculate_kehadiran_per_kelas(df_total_kehadiran)

        if not df_kehadiran_kelas.empty:
            st.dataframe(df_kehadiran_kelas, use_container_width=True)
            
            excel_bytes_kelas = convert_df_to_excel(
                df_kehadiran_kelas, sheet_name="Kehadiran per Kelas"
            )
            st.download_button(
                label="Download Rekap Kehadiran Kelas",
                data=excel_bytes_kelas,
                file_name="Rekap_Kehadiran_Per_Kelas.xlsx",
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

with tab_postes:
    st.header("Ekstrak Nilai Postes")

    col_postes_1, col_postes_2 = st.columns(2)
    with col_postes_1:
        uploaded_siswa_postes = st.file_uploader(
            "Upload File Excel Nama Siswa",
            type=["xlsx", "xls", "xlsm"],
            key="uploader_psikotes_siswa",
        )
    with col_postes_2:
        uploaded_postes = st.file_uploader(
            "Upload File Postes",
            type=["xlsx", "xls", "xlsm"],
            key="uploader_postes_data",
        )

    if uploaded_siswa_postes is None or uploaded_postes is None:
        st.info("Silakan upload kedua file Excel untuk melanjutkan.")
    else:
        excel_siswa_postes = pd.ExcelFile(uploaded_siswa_postes)
        excel_postes = pd.ExcelFile(uploaded_postes)

        selected_sheet_siswa_postes = st.selectbox(
            "Pilih Sheet Nama Siswa:",
            excel_siswa_postes.sheet_names,
            key="sheet_siswa_select_postes",
        )

        st.subheader("Pilih Sheet Postes")
        target_subtests_postes = st.multiselect(
            "Pilih Subtes yang Ingin Diekstrak:",
            options=excel_postes.sheet_names,
            default=excel_postes.sheet_names[: min(0, len(excel_postes.sheet_names))],
            key="multiselect_subtests_postes",
        )

        if not target_subtests_postes:
            st.warning("Pilih minimal 1 subtes.")
        else:
            df_hasil_postes = process_postes(
                uploaded_siswa_postes, uploaded_postes, selected_sheet_siswa_postes, target_subtests_postes
            )

            st.subheader("Tabel Nilai Siswa")
            st.dataframe(df_hasil_postes, use_container_width=True)

            excel_bytes_postes = convert_df_to_excel(
                df_hasil_postes, sheet_name="Hasil Nilai Postes"
            )
            st.download_button(
                label="Download Hasil Nilai",
                data=excel_bytes_postes,
                file_name="Hasil_Nilai_Postes.xlsx",
                key="download_postes",
            )

            st.divider()

            st.subheader("Rata-Rata Nilai per Kelas")

            score_cols_postes = [
                col for col in df_hasil_postes.columns if col.startswith("Nilai ")
            ]

            kelas_col_postes = next(
                (
                    c
                    for c in ["KELAS (DI PRIORITY)"]
                    if c in df_hasil_postes.columns
                ),
                None,
            )

            if score_cols_postes and kelas_col_postes:
                df_calc_postes = df_hasil_postes.copy()

                for col in score_cols_postes:
                    df_calc_postes[col] = pd.to_numeric(df_calc_postes[col], errors="coerce")

                df_avg_kelas_postes = (
                    df_calc_postes.groupby(kelas_col_postes)[score_cols_postes].mean().round(2).reset_index()
                )
                df_avg_kelas_postes.index = range(1, len(df_avg_kelas_postes) + 1)
                df_avg_kelas_postes.index.name = "No"

                st.dataframe(df_avg_kelas_postes, use_container_width=True)

                fig_postes = px.bar(
                    df_avg_kelas_postes,
                    x=kelas_col_postes,
                    y=score_cols_postes,
                    barmode="group",
                    title="Rata-Rata Nilai Postes per Kelas",
                    labels={
                        kelas_col_postes: "Kelas",
                        "value": "Nilai Rata-Rata",
                        "variable": "Subtes",
                    },
                    text_auto=".2f",
                )

                fig_postes.update_layout(
                    xaxis_title="Kelas",
                    yaxis_title="Nilai Rata-Rata",
                    margin=dict(l=20, r=20, t=50, b=20),
                )

                st.plotly_chart(fig_postes, use_container_width=True)

                excel_bytes_avg_postes = convert_df_to_excel(
                    df_avg_kelas_postes, sheet_name="Rata-Rata per Kelas"
                )
                st.download_button(
                    label="Download Nilai Rata-Rata Kelas",
                    data=excel_bytes_avg_postes,
                    file_name="Rata_Rata_Nilai_Per_Kelas.xlsx",
                    key="download_avg_kelas",
                )