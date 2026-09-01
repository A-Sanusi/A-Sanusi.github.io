import io
import re
import zipfile
from collections import defaultdict
import streamlit as st
from pypdf import PdfWriter


def extract_student_name(filename: str) -> str:
    name_part = filename.rsplit(".", 1)[0]

    rapor_match = re.match(
        r"^Rapor\s+(.*?)(?:\s+\d+[A-Z]?)?$", name_part, re.IGNORECASE
    )
    if rapor_match:
        return re.sub(r"\b\d+[A-Za-z]*$", "", rapor_match.group(1)).strip()

    if " - " in name_part:
        return name_part.split(" - ")[0].strip()

    return name_part


st.set_page_config(page_title="PDF Merger")
st.title("PDF Merger (biar cepet selesai hehe)")

uploaded_files = st.file_uploader(
    "Pilih file", type=["pdf"], accept_multiple_files=True
)

if uploaded_files:
    if st.button("Satukan PDF", type="primary"):
        student_files = defaultdict(list)

        for file in uploaded_files:
            student = extract_student_name(file.name)
            student_files[student].append(file)

        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for student, files in student_files.items():
                writer = PdfWriter()

                sorted_files = sorted(
                    files,
                    key=lambda f: (
                        0 if "rapor" in f.name.lower() else 1,
                        f.name.lower(),
                    ),
                )

                for pdf_file in sorted_files:
                    writer.append(pdf_file)

                pdf_output_stream = io.BytesIO()
                writer.write(pdf_output_stream)
                writer.close()

                safe_student_name = re.sub(r"[^\w\s-]", "", student).strip()
                merged_filename = f"Rapor Psikotes {safe_student_name}.pdf"

                zip_file.writestr(
                    merged_filename, pdf_output_stream.getvalue()
                )

        zip_buffer.seek(0)
        st.success(
            f"{len(student_files)} PDF siswa sukses disatukan"
        )

        st.download_button(
            label="Download semua PDF",
            data=zip_buffer,
            file_name="Merged PDF psikotes.zip",
            mime="application/zip",
        )
