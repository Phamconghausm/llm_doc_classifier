# utils/extractor.py
def extract_text(file_path):
    import os
    import pdfplumber
    import docx2txt

    ext = os.path.splitext(file_path)[1].lower()
    text = ""

    # =======================
    # PDF
    # =======================
    if ext == ".pdf":

        # 1) Kiểm tra đúng PDF thật
        try:
            with open(file_path, "rb") as f:
                header = f.read(10)
                if b"%PDF" not in header:
                    print(f"[extract_text] Not real PDF: {file_path}")
                    return ""
        except:
            return ""

        # 2) Mở pdfplumber
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            print(f"[extract_text] pdfplumber error: {e}")
            return ""

    # =======================
    # DOCX
    # =======================
    elif ext == ".docx":
        try:
            text = docx2txt.process(file_path) or ""
        except Exception as e:
            print(f"[extract_text] docx2txt error: {e}")
            return ""

    # =======================
    # TXT
    # =======================
    else:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except Exception as e:
            print(f"[extract_text] text-file read error: {e}")
            return ""

    return text.strip()
