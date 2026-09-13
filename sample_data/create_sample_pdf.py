import fitz # PyMuPDF
import json
import os

def create_pdf():
    json_path = os.path.join(os.path.dirname(__file__), "sample_quiz.json")
    pdf_path = os.path.join(os.path.dirname(__file__), "sample_questions.pdf")

    with open(json_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    doc = fitz.open()
    page = doc.new_page(width=595, height=842) # A4
    y = 50

    page.insert_text((50, y), "QUIZARENA SAMPLE QUESTION PAPER", fontsize=16, fontname="helv", color=(0.1, 0.2, 0.5))
    y += 40

    for idx, q in enumerate(questions, start=1):
        if y > 750:
            page = doc.new_page(width=595, height=842)
            y = 50

        # Question header
        q_header = f"Q{idx}. {q['question_text']}"
        page.insert_text((50, y), q_header, fontsize=11, fontname="helv")
        y += 20

        # Options
        for opt in q['options']:
            page.insert_text((70, y), opt, fontsize=10, fontname="helv")
            y += 16

        # Answer
        page.insert_text((70, y), f"Answer: {q['correct_answer']}", fontsize=10, fontname="helv", color=(0, 0.5, 0.2))
        y += 16

        if q.get('explanation'):
            page.insert_text((70, y), f"Explanation: {q['explanation']}", fontsize=9, fontname="helv", color=(0.3, 0.3, 0.3))
            y += 18

        y += 10 # spacing

    doc.save(pdf_path)
    print(f"Generated sample PDF at: {pdf_path}")

if __name__ == "__main__":
    create_pdf()
