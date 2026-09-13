import re

def parse_questions_from_text(raw_text: str) -> list:
    questions = []
    if not raw_text or not raw_text.strip():
        return questions

    # Split into potential question blocks by matching Q1., Q2., 1., 2. or Question 1:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    
    current_q = None
    
    # Patterns
    q_start_pattern = re.compile(r'^(?:Q(?:uestion)?\s*\d+[\.\:]?|\d+[\.\)])\s*(.+)', re.IGNORECASE)
    opt_pattern = re.compile(r'^[\(\[\{]?([A-E])[\)\}\]\.]?\s*(.+)', re.IGNORECASE)
    ans_pattern = re.compile(r'^(?:Answer|Ans|Correct\s*Answer|Correct)\s*[\:\=]?\s*[\(\[\{]?([A-E])[\)\}\]\.]?', re.IGNORECASE)
    exp_pattern = re.compile(r'^(?:Explanation|Explain|Note)\s*[\:\=]?\s*(.+)', re.IGNORECASE)

    for line in lines:
        # Check answer pattern
        ans_match = ans_pattern.match(line)
        if ans_match and current_q:
            current_q["correct_answer"] = ans_match.group(1).upper()
            continue

        # Check explanation pattern
        exp_match = exp_pattern.match(line)
        if exp_match and current_q:
            current_q["explanation"] = exp_match.group(1)
            continue

        # Check question start pattern
        q_match = q_start_pattern.match(line)
        if q_match:
            # Finalize previous question if valid
            if current_q and current_q["question_text"]:
                finalize_question(current_q, questions)
            
            q_text = q_match.group(1).strip()
            current_q = {
                "question_text": q_text,
                "options": [],
                "correct_answer": "A",
                "explanation": ""
            }
            continue

        # Check option pattern
        opt_match = opt_pattern.match(line)
        if opt_match and current_q:
            letter = opt_match.group(1).upper()
            val = opt_match.group(2).strip()
            current_q["options"].append(f"{letter}. {val}")
            continue

        # Continuation line
        if current_q:
            if not current_q["options"]:
                current_q["question_text"] += " " + line
            elif current_q["options"]:
                # Continuation of last option
                current_q["options"][-1] += " " + line

    if current_q and current_q["question_text"]:
        finalize_question(current_q, questions)

    return questions

def finalize_question(q_dict: dict, target_list: list):
    # Ensure options are present (if missing, provide placeholders)
    if not q_dict["options"] or len(q_dict["options"]) < 2:
        q_dict["options"] = ["A. Option A", "B. Option B", "C. Option C", "D. Option D"]
    
    # Ensure correct answer letter matches available options
    letters = [opt[0].upper() for opt in q_dict["options"] if len(opt) > 0 and opt[0].isalpha()]
    if q_dict["correct_answer"] not in letters and letters:
        q_dict["correct_answer"] = letters[0]

    target_list.append(q_dict)
