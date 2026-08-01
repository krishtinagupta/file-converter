import streamlit as st
import pandas as pd
import pdfplumber
from fpdf import FPDF

# ---------- READ FUNCTIONS ----------
def read_csv(path):
    return pd.read_csv(path)

def read_pdf(path):
    all_rows = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                all_rows.extend(table)
    if not all_rows:
        raise ValueError("No table were detected in the PDF. It may be a scanned or image based PDF.")
    df = pd.DataFrame(all_rows[1:], columns=all_rows[0])
    return df

def read_json(path):
    return pd.read_json(path)

def read_excel(path):
    return pd.read_excel(path)

def read_xml(path):
    return pd.read_xml(path)

def read_txt(path):
    return pd.read_csv(path, delimiter="\t")


# ---------- WRITE FUNCTIONS ----------
def write_csv(df, path):
    df.to_csv(path, index=False)

def write_pdf(df, path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 8, " | ".join(str(col) for col in df.columns), ln=True)
    for row in df.itertuples(index=False):
        pdf.cell(0, 8, " | ".join(str(x) for x in row), ln=True)
    pdf.output(path)

def write_json(df, path):
    df.to_json(path, orient="records", indent=2)

def write_excel(df, path):
    df.to_excel(path, index=False)

def write_xml(df, path):
    df.to_xml(path, index=False)

def write_txt(df, path):
    df.to_csv(path, sep="\t", index=False)

# ---------- CONVERT FUNCTION ----------
def convert(input_path, output_path, from_format, to_format):
    readers = {"csv": read_csv, "json": read_json, "excel": read_excel,
               "xml": read_xml, "txt": read_txt, "pdf": read_pdf}
    writers = {"csv": write_csv, "json": write_json, "excel": write_excel,
               "xml": write_xml, "txt": write_txt, "pdf": write_pdf}
    df = readers[from_format](input_path)
    writers[to_format](df, output_path)

# ---------- EXTENSION -> FORMAT MAPPING ----------
ext_to_format = {
    "csv": "csv",
    "json": "json",
    "xlsx": "excel",
    "xls": "excel",
    "xml": "xml",
    "txt": "txt",
    "pdf": "pdf",
}

format_list = ["csv", "json", "excel", "xml", "txt", "pdf"]

# ---------- STREAMLIT UI ----------
st.title("📁 File Converter and Comparison Tool")

uploaded_file = st.file_uploader("File upload, ", type=["csv", "json", "xlsx", "xml", "txt", "pdf"])

# Detect format from uploaded file's extension
detected_format = None
if uploaded_file is not None:
    file_ext = uploaded_file.name.split(".")[-1].lower()
    detected_format = ext_to_format.get(file_ext)

if detected_format:
    from_format = st.selectbox(
        "File format starting type?",
        format_list,
        index=format_list.index(detected_format),
        disabled=True
    )
else:
    from_format = st.selectbox("File format starting type?", format_list)

to_format = st.selectbox("Format converting?", format_list)

if st.button("Convert file") and uploaded_file is not None:
    input_path = "temp_input." + (from_format if from_format != "excel" else "xlsx")
    with open(input_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    output_path = "converted_output." + (to_format if to_format != "excel" else "xlsx")

    try:
        convert(input_path, output_path, from_format, to_format)
        st.success("Conversion successful")
        with open(output_path, "rb") as f:
            st.download_button("Download Converted File", f, file_name=output_path)
    except Exception as e:
        st.error(f"Error: {e}")