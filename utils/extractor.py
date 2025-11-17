# utils/extractor.py
import os
import pdfplumber
import docx2txt

def extract_text(file_path):
    """
    Extract text from PDF, DOCX, or TXT.
    Returns clean text or empty string if extraction fails.
    """
    ext = os.path.splitext(file_path)[1].lower()
    text = ""

    # -----------------------------
    # PDF
    # -----------------------------
    if ext == ".pdf":
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

        except Exception as e:
            print(f"[extract_text] pdfplumber error: {e}")
            return ""   # PDF lỗi hoặc không phải PDF thật → trả empty luôn

    # -----------------------------
    # DOCX
    # -----------------------------
    elif ext == ".docx":
        try:
            text = docx2txt.process(file_path) or ""
        except Exception as e:
            print(f"[extract_text] docx2txt error: {e}")
            return ""

    # -----------------------------
    # TXT / JSON / CSV / Others text-based
    # -----------------------------
    else:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except Exception as e:
            print(f"[extract_text] text-file read error: {e}")
            return ""

    # Clean output
    return text.strip()
