# utils/llm_client.py
import os, json
from openai import OpenAI
from dotenv import load_dotenv
from utils.category_mapping import CATEGORY_MAP

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def _build_prompt(text):
    # include category examples to force the model to choose one
    categories_block = "\n".join([f"{k}: {v}" for k, v in CATEGORY_MAP.items()])
    return f"""
You are an assistant that CLASSIFIES enterprise / business documents (Vietnamese or international).
You MUST choose exactly ONE category from the list below (use the category key).
Do NOT invent new categories.

Categories:
{categories_block}

Task:
1) Read the document.
2) Choose one category key from above.
3) Produce a short 1-2 sentence summary.
4) Give a confidence between 0 and 100 (integer).

Return ONLY valid JSON with keys: type, summary, confidence

DOCUMENT (first 3000 chars):
{text[:3000]}
"""

def classify_document(text, max_tokens=1000):
    prompt = _build_prompt(text)
    try:
        res = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": "You classify documents accurately and return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=max_tokens,
        )
        raw = res.choices[0].message.content.strip()
    except Exception as e:
        # return fallback
        print(f"[llm_client] LLM request failed: {e}")
        return json.dumps({"type": "OTHERS", "summary": "LLM error", "confidence": 0})

    # Try to parse JSON robustly (sometimes model returns code blocks)
    try:
        # remove triple backticks if present
        if raw.startswith("```"):
            # extract content between ```json ... ```
            parts = raw.split("```")
            # pick the first block that looks like json
            candidate = None
            for p in parts:
                p_strip = p.strip()
                if p_strip.startswith("{") and p_strip.endswith("}"):
                    candidate = p_strip
                    break
            if candidate:
                raw = candidate

        data = json.loads(raw)
    except Exception as e:
        # fallback: try to extract {...} substring
        import re
        m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
            except Exception as e2:
                print(f"[llm_client] JSON parse error: {e2}; raw:\n{raw}")
                data = {"type": "OTHERS", "summary": raw[:300], "confidence": 0}
        else:
            print(f"[llm_client] Cannot parse LLM output as JSON; raw:\n{raw}")
            data = {"type": "OTHERS", "summary": raw[:300], "confidence": 0}

    # sanitize output
    data.setdefault("type", "OTHERS")
    data.setdefault("summary", "")
    try:
        data["confidence"] = int(data.get("confidence", 0))
    except Exception:
        data["confidence"] = 0

    # Ensure type is one of CATEGORY_MAP keys
    if data["type"] not in CATEGORY_MAP:
        # If LLM chose human readable, try to map by key presence
        found = None
        for key in CATEGORY_MAP:
            if key.lower() in str(data["type"]).lower():
                found = key
                break
        data["type"] = found or "OTHERS"

    return json.dumps(data, ensure_ascii=False)
