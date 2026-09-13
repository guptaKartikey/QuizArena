import os
import pytest
from pdf_processor.parser import extract_text_from_pdf
from pdf_processor.question_extractor import parse_questions_from_text

def test_parse_sample_pdf():
    pdf_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sample_data", "sample_questions.pdf"))
    assert os.path.exists(pdf_path), "sample_questions.pdf must exist"

    with open(pdf_path, "rb") as f:
        content = f.read()

    text = extract_text_from_pdf(content)
    assert len(text) > 0, "Extracted text should not be empty"

    questions = parse_questions_from_text(text)
    assert len(questions) >= 10, f"Expected at least 10 extracted questions, got {len(questions)}"
    
    first = questions[0]
    assert "Red Planet" in first["question_text"] or "capital" in first["question_text"]
    assert len(first["options"]) >= 2
    assert first["correct_answer"] in ["A", "B", "C", "D"]
