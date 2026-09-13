import os
import re
import pandas as pd
import fitz  # PyMuPDF
import pdfplumber

def extract_text_from_pdf(file_path_or_bytes) -> str:
    text = ""
    # Try PyMuPDF first
    try:
        if isinstance(file_path_or_bytes, bytes):
            doc = fitz.open(stream=file_path_or_bytes, filetype="pdf")
        else:
            doc = fitz.open(file_path_or_bytes)
        
        for page in doc:
            text += page.get_text("text") + "\n"
        
        if text.strip():
            return text
    except Exception as e:
        print(f"PyMuPDF extraction failed/fallback: {e}")

    # Fallback to pdfplumber
    try:
        if isinstance(file_path_or_bytes, bytes):
            import io
            file_obj = io.BytesIO(file_path_or_bytes)
        else:
            file_obj = file_path_or_bytes

        with pdfplumber.open(file_obj) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"pdfplumber extraction failed: {e}")

    return text

def parse_txt_content(content: str) -> str:
    return content

def parse_csv_file(file_path_or_bytes) -> list:
    df = pd.read_csv(file_path_or_bytes)
    return parse_dataframe(df)

def parse_excel_file(file_path_or_bytes) -> list:
    df = pd.read_excel(file_path_or_bytes)
    return parse_dataframe(df)

def parse_dataframe(df: pd.DataFrame) -> list:
    questions = []
    # Normalize column names
    col_map = {str(c).strip().lower(): c for c in df.columns}
    
    q_col = col_map.get("question") or col_map.get("question_text") or df.columns[0]
    ans_col = col_map.get("answer") or col_map.get("correct_answer")
    exp_col = col_map.get("explanation")
    
    opt_a_col = col_map.get("option a") or col_map.get("a") or col_map.get("option_a")
    opt_b_col = col_map.get("option b") or col_map.get("b") or col_map.get("option_b")
    opt_c_col = col_map.get("option c") or col_map.get("c") or col_map.get("option_c")
    opt_d_col = col_map.get("option d") or col_map.get("d") or col_map.get("option_d")
    opt_e_col = col_map.get("option e") or col_map.get("e") or col_map.get("option_e")

    for _, row in df.iterrows():
        q_text = str(row[q_col]).strip() if pd.notna(row[q_col]) else ""
        if not q_text:
            continue
        
        opts = []
        if opt_a_col and pd.notna(row[opt_a_col]):
            val = str(row[opt_a_col]).strip()
            opts.append(f"A. {val}" if not val.startswith("A.") else val)
        if opt_b_col and pd.notna(row[opt_b_col]):
            val = str(row[opt_b_col]).strip()
            opts.append(f"B. {val}" if not val.startswith("B.") else val)
        if opt_c_col and pd.notna(row[opt_c_col]):
            val = str(row[opt_c_col]).strip()
            opts.append(f"C. {val}" if not val.startswith("C.") else val)
        if opt_d_col and pd.notna(row[opt_d_col]):
            val = str(row[opt_d_col]).strip()
            opts.append(f"D. {val}" if not val.startswith("D.") else val)
        if opt_e_col and pd.notna(row[opt_e_col]):
            val = str(row[opt_e_col]).strip()
            opts.append(f"E. {val}" if not val.startswith("E.") else val)

        ans = str(row[ans_col]).strip().upper() if ans_col and pd.notna(row[ans_col]) else "A"
        # Extract letter if full text
        if ans and len(ans) > 1:
            match = re.search(r'\b([A-E])\b', ans)
            ans = match.group(1) if match else "A"

        exp = str(row[exp_col]).strip() if exp_col and pd.notna(row[exp_col]) else ""

        questions.append({
            "question_text": q_text,
            "options": opts if opts else ["A. Option 1", "B. Option 2", "C. Option 3", "D. Option 4"],
            "correct_answer": ans if ans in ["A", "B", "C", "D", "E"] else "A",
            "explanation": exp
        })
        
    return questions
