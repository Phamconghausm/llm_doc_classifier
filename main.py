# main.py
import os, json
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from utils.extractor import extract_text
from utils.llm_client import classify_document
from utils.db import init_db, SessionLocal, Document, Category
from crawler import crawl_files
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Cho phép frontend localhost truy cập
origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,      # frontend URL
    allow_credentials=True,
    allow_methods=["*"],        # GET, POST, PUT...
    allow_headers=["*"],        # tất cả header
)
init_db()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def root():
    return {"message": "LLM Document Classifier API is running"}

# Upload file
@app.post("/upload")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    save_dir = "data/raw"
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, file.filename)

    # Save file
    try:
        with open(save_path, "wb") as f:
            f.write(await file.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot save file: {e}")

    # Extract text
    text = extract_text(save_path)
    if not text:
        raise HTTPException(status_code=400, detail="Cannot extract text from file")

    # Classify
    result = classify_document(text)
    try:
        data = json.loads(result)
    except Exception:
        data = {"type": "OTHERS", "summary": "Invalid LLM output", "confidence": 0}

    # Persist
    doc = Document(
        filename=file.filename,
        doc_type=data.get("type"),
        summary=data.get("summary"),
        confidence=data.get("confidence", 0),
        source="manual"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {"status": "ok", "document_id": doc.id, "classification": data}

# Crawl endpoint
@app.post("/crawl")
def run_crawl(max_files: int = 5, db: Session = Depends(get_db)):
    files = crawl_files(max_files=max_files)
    new_files = []
    for filename in files:
        path = os.path.join("data/raw", filename)

        exists = db.query(Document).filter(Document.filename == filename).first()
        if exists:
            continue

        text = extract_text(path)
        if not text:
            continue

        result = classify_document(text)
        try:
            data = json.loads(result)
        except Exception:
            data = {"type": "OTHERS", "summary": "Invalid LLM output", "confidence": 0}

        doc = Document(
            filename=filename,
            doc_type=data.get("type"),
            summary=data.get("summary"),
            confidence=data.get("confidence", 0),
            source="crawl"
        )
        db.add(doc)
        new_files.append(filename)

    db.commit()
    return {"crawled": len(new_files), "files_added": new_files}

# Get documents
@app.get("/documents")
def get_documents(db: Session = Depends(get_db)):
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "type": d.doc_type,
            "confidence": d.confidence,
            "source": d.source,
            "created_at": d.created_at.isoformat()
        } for d in docs
    ]

# Stats
@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    docs = db.query(Document.doc_type).all()
    stats = {}
    for (t,) in docs:
        if t:
            stats[t] = stats.get(t, 0) + 1
    return {"stats": stats}

# categories listing
@app.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    items = db.query(Category).all()
    return [{"key": c.key, "description": c.description} for c in items]
