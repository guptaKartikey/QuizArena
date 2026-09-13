import os
import json
import httpx

GROK_API_KEY = os.getenv("GROK_API_KEY", os.getenv("GROQ_API_KEY", os.getenv("GEMINI_API_KEY", "")))

def generate_questions_with_ai(topic: str, count: int = 5, api_key: str = None) -> list:
    """
    Generates multiple-choice questions using the Grok/Groq AI API.
    Returns a list of dictionaries with keys: question, options, answer, explanation.
    """
    key = api_key or GROK_API_KEY
    if not key or not key.strip():
        raise ValueError("AI API key is missing. Please provide a valid Grok/Groq API key.")

    # Determine endpoint and models
    if key.startswith("xai-"):
        url = "https://api.x.ai/v1/chat/completions"
        candidate_models = ["grok-2-latest", "grok-beta"]
    else:
        url = "https://api.groq.com/openai/v1/chat/completions"
        candidate_models = ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b"]

    prompt = f"""
Generate exactly {count} multiple-choice quiz questions about the topic: "{topic}".

Rules:
1. Each question must have exactly 4 options labeled "A. ...", "B. ...", "C. ...", "D. ...".
2. Only one option is correct. "answer" must be one of "A", "B", "C", "D".
3. Provide a clear explanation for the correct answer.

Output format: You MUST reply ONLY with a valid JSON array of objects. Do NOT include any markdown code blocks or conversational text.
Example structure:
[
  {{
    "question": "What is the capital of France?",
    "options": ["A. Berlin", "B. Madrid", "C. Paris", "D. Rome"],
    "answer": "C",
    "explanation": "Paris is the capital and most populous city of France."
  }}
]
"""

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    last_error = None
    content = ""

    with httpx.Client(timeout=45.0) as client:
        for model in candidate_models:
            try:
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are a professional quiz generator. Respond strictly with raw JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.6
                }
                resp = client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    break
                else:
                    last_error = f"{resp.status_code}: {resp.text}"
            except Exception as e:
                last_error = str(e)

    if not content:
        raise RuntimeError(f"AI generation failed: {last_error}")

    # Strip code block wrappers if model added any
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            # Check for inner array
            for v in parsed.values():
                if isinstance(v, list):
                    parsed = v
                    break
        if not isinstance(parsed, list):
            raise ValueError("Response is not a JSON list of questions.")
        return parsed
    except Exception as err:
        raise ValueError(f"Could not parse AI response into questions: {err}\nResponse text: {content}")
