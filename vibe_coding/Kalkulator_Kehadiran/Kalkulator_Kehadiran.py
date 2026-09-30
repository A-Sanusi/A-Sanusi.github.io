import pandas as pd
import numpy as np
import re
import io
import streamlit as st

st.set_page_config(page_title = "Kalkulator Kehadiran Kelas")
st.link_button("Menu", "https://a-sanusi.github.io/vibe_coding/vibe_coding.html")
st.title("Kalkulator Kehadiran")

uploaded_siswa = st.file_uploader(
    "Upload File Excel Siswa",
    type=["xlsx, xls, xlsm"],
    key="uploader_kehadiran_siswa",
)

if uploaded_siswa is None:
    st.info("Silakan upload file Excel")
else:
    excel_siswa = pd.ExcelFile(uploaded_siswa)
    selected_sheet_siswa = st.selectbox(
        "Pilih Sheet Siswa Utama:",
        excel_siswa.sheet_names,
        key = "sheet_selected_siswa",
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
                excel_siswa.sheet_names,
                key=f"select_sheet_kehadiran{i}",
            )
    
    target_sheets = list(selecting.values())
