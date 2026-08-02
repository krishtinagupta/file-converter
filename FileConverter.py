import streamlit as st
import pandas as pd
import pdfplumber
from fpdf import FPDF

def read_csv(path):
    return pd.read_csv(path)

def read_pdf(path):
    all_rows = []

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            table = page.extract_table()

            if not table:
                table = page.extract_table(table_settings={
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                })

            if table:
                all_rows.extend(table)

    if all_rows:
        max_cols = max(len(row) for row in all_rows)
        all_rows = [
            list(row) + [None] * (max_cols - len(row))
            for row in all_rows
        ]

        header = all_rows[0]
        seen = {}
        clean_header = []
        for i, h in enumerate(header):
            name = h if h not in (None, "") else f"col_{i}"
            if name in seen:
                seen[name] += 1
                name = f"{name}_{seen[name]}"
            else:
                seen[name] = 0
            clean_header.append(name)

        df = pd.DataFrame(all_rows[1:], columns=clean_header)
        return df

    with pdfplumber.open(path) as pdf:
        lines = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                lines.extend(text.split("\n"))

    if not lines:
        raise ValueError(
            "No text found in the PDF. This looks like a scanned/image-based PDF — "
            "OCR (e.g. pytesseract) is required before converting it."
        )

    rows = [line.split() for line in lines if line.strip()]
    max_cols = max(len(r) for r in rows)
    rows = [r + [""] * (max_cols - len(r)) for r in rows]

    df = pd.DataFrame(rows[1:], columns=rows[0])
    return df

def read_json(path):
    return pd.read_json(path)

def read_excel(path):
    return pd.read_excel(path)

def read_xml(path):
    return pd.read_xml(path)

def read_txt(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.read().splitlines()
    return pd.DataFrame({"text": lines})


def write_csv(df, path):
    df.to_csv(path, index=False)

def write_pdf(df, path, from_format="csv"):
    if from_format == "json":
        _write_pdf_as_records(df, path)
    elif from_format == "txt":
        _write_pdf_as_plain_text(df, path)
    else:
        _write_pdf_as_table(df, path)


def _write_pdf_as_table(df, path):
    pdf = FPDF(orientation="L")
    pdf.add_page()

    num_cols = len(df.columns)
    if num_cols <= 5:
        font_size = 10
    elif num_cols <= 8:
        font_size = 8
    else:
        font_size = 6

    pdf.set_font("Arial", size=font_size)

    page_width = pdf.w - 2 * pdf.l_margin
    col_width = page_width / num_cols
    row_height = pdf.font_size * 1.5

    def print_row(values, bold=False):
        pdf.set_font("Arial", style="B" if bold else "", size=font_size)
        y_start = pdf.get_y()
        max_lines = 1

        for val in values:
            text = str(val)
            lines = pdf.multi_cell(col_width, row_height, text, border=0, align="L", split_only=True)
            max_lines = max(max_lines, len(lines))

        cell_height = row_height * max_lines

        if y_start + cell_height > pdf.h - pdf.b_margin:
            pdf.add_page()
            y_start = pdf.get_y()
            pdf.set_font("Arial", style="B" if bold else "", size=font_size)

        for val in values:
            x = pdf.get_x()
            y = pdf.get_y()
            pdf.multi_cell(col_width, cell_height / max_lines, str(val), border=1, align="L")
            pdf.set_xy(x + col_width, y)

        pdf.ln(cell_height)

    print_row(list(df.columns), bold=True)
    for row in df.itertuples(index=False):
        print_row(list(row))

    pdf.output(path)


def _wrap_text_lines(pdf, text, max_width):
    lines = []
    for raw_line in str(text).split("\n"):
        words = raw_line.split(" ")
        current = ""
        for word in words:
            while pdf.get_string_width(word) > max_width:
                lo, hi = 1, len(word)
                fit = 1
                while lo <= hi:
                    mid = (lo + hi) // 2
                    if pdf.get_string_width(word[:mid]) <= max_width:
                        fit = mid
                        lo = mid + 1
                    else:
                        hi = mid - 1
                if current:
                    lines.append(current)
                    current = ""
                lines.append(word[:fit])
                word = word[fit:]

            candidate = (current + " " + word).strip() if current else word
            if pdf.get_string_width(candidate) <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word

        lines.append(current)

    return lines if lines else [""]


def _write_pdf_as_records(df, path):
    pdf = FPDF(orientation="P")
    pdf.add_page()
    pdf.set_font("Arial", size=10)

    page_width = pdf.w - 2 * pdf.l_margin
    line_height = 6

    for i, row in enumerate(df.itertuples(index=False)):
        for col, val in zip(df.columns, row):
            text = f"{col}: {val}"
            for line in _wrap_text_lines(pdf, text, page_width):
                if pdf.get_y() + line_height > pdf.h - pdf.b_margin:
                    pdf.add_page()
                pdf.cell(page_width, line_height, line, ln=1)

        if pdf.get_y() + line_height > pdf.h - pdf.b_margin:
            pdf.add_page()
        pdf.ln(4)

    pdf.output(path)


def _write_pdf_as_plain_text(df, path):
    pdf = FPDF(orientation="P")
    pdf.add_page()
    pdf.set_font("Arial", size=11)

    page_width = pdf.w - 2 * pdf.l_margin
    line_height = 6

    def print_text(text):
        for line in _wrap_text_lines(pdf, text, page_width):
            if pdf.get_y() + line_height > pdf.h - pdf.b_margin:
                pdf.add_page()
            pdf.cell(page_width, line_height, line, ln=1)

    if list(df.columns) == ["text"]:
        for val in df["text"]:
            print_text(str(val))
        pdf.output(path)
        return

    print_text("\t".join(str(col) for col in df.columns))
    pdf.ln(2)

    for row in df.itertuples(index=False):
        print_text("\t".join(str(x) for x in row))

    pdf.output(path)

def write_json(df, path):
    df.to_json(path, orient="records", indent=2)

def write_excel(df, path):
    df.to_excel(path, index=False)

def write_xml(df, path):
    df.to_xml(path, index=False)

def write_txt(df, path):
    if list(df.columns) == ["text"]:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(str(v) for v in df["text"]))
    else:
        df.to_csv(path, sep="\t", index=False)

def convert(input_path, output_path, from_format, to_format):
    readers = {"csv": read_csv, "json": read_json, "excel": read_excel,
               "xml": read_xml, "txt": read_txt, "pdf": read_pdf}
    writers = {"csv": write_csv, "json": write_json, "excel": write_excel,
               "xml": write_xml, "txt": write_txt, "pdf": write_pdf}
    df = readers[from_format](input_path)

    if to_format == "pdf":
        writers[to_format](df, output_path, from_format=from_format)
    else:
        writers[to_format](df, output_path)

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

st.title("📁 File Converter and Comparison Tool")

uploaded_file = st.file_uploader("File upload, ", type=["csv", "json", "xlsx", "xml", "txt", "pdf"])

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