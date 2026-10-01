import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Analisis Nilai Try Out", layout="wide")

st.title("Dashboard Analisis Nilai Try Out")

# Sidebar - File Upload
uploaded_file = st.sidebar.file_uploader(
    "Upload File Excel / CSV", type=["xlsx", "csv"]
)

if uploaded_file is not None:
    if uploaded_file.name.endswith(".csv"):
        df_hasil = pd.read_csv(uploaded_file)
    else:
        df_hasil = pd.read_excel(uploaded_file)
else:
    # Default sample data structure for testing
    st.info("Menampilkan data sampel. Silakan upload file Anda di sidebar.")
    df_hasil = pd.DataFrame(
        {
            "KELAS (DI PRIORITY)": [
                "12 IPA 1",
                "12 IPA 1",
                "12 IPA 2",
                "12 IPA 2",
            ],
            "Nilai Matematika": [80, 85, 70, 75],
            "Nilai Fisika": [75, 90, 65, 80],
            "Nilai Kimia": [88, 92, 72, 78],
        }
    )

# Create Tabs
tab_to_tka, tab_lain = st.tabs(["Analisis TO/TKA", "Laporan Lain"])

with tab_to_tka:
    st.subheader("Rata-Rata Nilai per Kelas")

    # Detect all subtest columns starting with 'Nilai '
    score_cols = [col for col in df_hasil.columns if col.startswith("Nilai ")]

    if score_cols:
        df_calc = df_hasil.copy()

        # Parse score values safely as numeric
        for col in score_cols:
            df_calc[col] = pd.to_numeric(df_calc[col], errors="coerce")

        cols_to_avg = score_cols

        # Group by class and calculate average
        df_avg_kelas = (
            df_calc.groupby("KELAS (DI PRIORITY)")[cols_to_avg]
            .mean()
            .round(2)
            .reset_index()
        )
        df_avg_kelas.index = range(1, len(df_avg_kelas) + 1)
        df_avg_kelas.index.name = "No"

        # Table Display
        st.dataframe(df_avg_kelas, use_container_width=True)

        # Plotly Line Chart
        fig = px.line(
            df_avg_kelas,
            x="KELAS (DI PRIORITY)",
            y=cols_to_avg,
            markers=True,
            title="Rata-Rata Nilai Try Out per Kelas",
            labels={
                "KELAS (DI PRIORITY)": "Kelas",
                "value": "Nilai Rata-Rata",
                "variable": "Subtes / Kategori",
            },
        )

        fig.update_layout(
            xaxis_title="Kelas",
            yaxis_title="Nilai Rata-Rata",
            legend_title="Kategori",
            hovermode="x unified",
            margin=dict(l=20, r=20, t=50, b=20),
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(
            "Tidak ditemukan kolom yang diawali dengan 'Nilai ' pada dataset."
        )

with tab_lain:
    st.write("Tab tambahan untuk analisis atau data lainnya.")
