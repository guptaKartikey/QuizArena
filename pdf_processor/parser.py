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
    if df.empty:
        return questions

    # Create normalized column mapping (lowercase, stripped, cleaned)
    def clean_col(c):
        return re.sub(r'[^a-z0-9]', '', str(c).strip().lower())

    col_map = {clean_col(c): c for c in df.columns}
    
    # Question text column
    q_col = (col_map.get("question") or col_map.get("questiontext") or 
             col_map.get("q") or col_map.get("questions") or 
             col_map.get("query") or col_map.get("title") or df.columns[0])
    
    # Answer column
    ans_col = (col_map.get("answer") or col_map.get("correctanswer") or 
               col_map.get("correct") or col_map.get("ans") or 
               col_map.get("rightanswer") or col_map.get("solution") or col_map.get("key"))
    
    # Explanation column
    exp_col = (col_map.get("explanation") or col_map.get("exp") or 
               col_map.get("reason") or col_map.get("description") or col_map.get("note"))
    
    # Option columns
    opt_a_col = (col_map.get("optiona") or col_map.get("a") or col_map.get("opta") or 
                 col_map.get("choicea") or col_map.get("opt1") or col_map.get("1"))
    opt_b_col = (col_map.get("optionb") or col_map.get("b") or col_map.get("optb") or 
                 col_map.get("choiceb") or col_map.get("opt2") or col_map.get("2"))
    opt_c_col = (col_map.get("optionc") or col_map.get("c") or col_map.get("optc") or 
                 col_map.get("choicec") or col_map.get("opt3") or col_map.get("3"))
    opt_d_col = (col_map.get("optiond") or col_map.get("d") or col_map.get("optd") or 
                 col_map.get("choiced") or col_map.get("opt4") or col_map.get("4"))
    opt_e_col = (col_map.get("optione") or col_map.get("e") or col_map.get("opte") or 
                 col_map.get("choicee") or col_map.get("opt5") or col_map.get("5"))

    for _, row in df.iterrows():
        q_text = str(row[q_col]).strip() if (q_col in row and pd.notna(row[q_col])) else ""
        if not q_text or q_text.lower() == "nan":
            continue
        
        raw_options = []
        raw_vals = []
        for idx, col in enumerate([opt_a_col, opt_b_col, opt_c_col, opt_d_col, opt_e_col]):
            letter = chr(65 + idx)
            if col and col in row and pd.notna(row[col]):
                val = str(row[col]).strip()
                if val and val.lower() != "nan":
                    # Remove trailing .0 from float conversion
                    if val.endswith(".0"):
                        val = val[:-2]
                    raw_vals.append(val)
                    # Add letter prefix if not already present
                    if re.match(r'^[A-Ea-e][\.\:\)]\s*', val):
                        formatted_opt = f"{val[0].upper()}. {val[2:].strip()}"
                    else:
                        formatted_opt = f"{letter}. {val}"
                    raw_options.append(formatted_opt)

        if not raw_options:
            raw_options = ["A. Option 1", "B. Option 2", "C. Option 3", "D. Option 4"]

        # Parse correct answer
        raw_ans = str(row[ans_col]).strip() if (ans_col and ans_col in row and pd.notna(row[ans_col])) else "A"
        if raw_ans.endswith(".0"):
            raw_ans = raw_ans[:-2]

        ans = "A"
        # 1. Numeric answer (1 -> A, 2 -> B, 3 -> C, 4 -> D, 5 -> E)
        if raw_ans in ["1", "2", "3", "4", "5"]:
            ans = chr(65 + int(raw_ans) - 1)
        # 2. Letter answer (A, B, C, D, E or (A), A., Option A)
        elif re.match(r'^\(?([A-Ea-e])[\.\:\)]?$', raw_ans.strip()):
            ans = raw_ans.strip().upper()[0]
        elif re.search(r'\b([A-Ea-e])\b', raw_ans):
            match = re.search(r'\b([A-Ea-e])\b', raw_ans)
            ans = match.group(1).upper()
        else:
            # 3. Text match against option raw values
            found = False
            raw_ans_lower = raw_ans.strip().lower()
            for idx, r_val in enumerate(raw_vals):
                if r_val.lower() == raw_ans_lower or raw_ans_lower in r_val.lower():
                    ans = chr(65 + idx)
                    found = True
                    break
            if not found:
                ans = "A"

        exp = str(row[exp_col]).strip() if (exp_col and exp_col in row and pd.notna(row[exp_col]) and str(row[exp_col]).lower() != "nan") else ""

        questions.append({
            "question_text": q_text,
            "options": raw_options,
            "correct_answer": ans,
            "explanation": exp
        })
        
    return questions
