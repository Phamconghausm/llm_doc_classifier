import os
import json
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from utils.extractor import extract_text
from utils.llm_client import classify_document
from utils.db import init_db, SessionLocal, Document, Category
from crawler import crawl_files

# ======================================================
# App config
# ======================================================

app = FastAPI(
    title="LLM Document Classifier API",
    version="1.0",
    description="API for document upload, classification, crawling, and retrieval."
)

# ======================================================
# CORS
# ======================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# Database Dependency
# ======================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

init_db()

# ======================================================
# Pydantic Schemas
# ======================================================

class DocumentResponse(BaseModel):
    id: int
    filename: str
    type: str
    confidence: float
    source: str
    created_at: str


class DocumentDetailResponse(BaseModel):
    id: int
    filename: str
    doc_type: str
    summary: str
    confidence: float
    source: str
    created_at: str


class DocumentContentResponse(BaseModel):
    document_id: int
    content: str


# ======================================================
# Root
# ======================================================

@app.get("/")
def root():
    return {"message": "LLM Document Classifier API is running"}


# ======================================================
# Upload File
# ======================================================

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

    # Classify via LLM
    result = classify_document(text)
    try:
        data = json.loads(result)
    except Exception:
        data = {"type": "OTHERS", "summary": "Invalid LLM output", "confidence": 0}

    # Save to database
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

    return {
        "status": "ok",
        "document_id": doc.id,
        "classification": data
    }


# ======================================================
# Crawl Documents
# ======================================================

@app.post("/crawl")
def run_crawl(max_files: int = 5, db: Session = Depends(get_db)):
    files = crawl_files(max_files=max_files)
    new_files = []

    for filename in files:
        path = os.path.join("data/raw", filename)

        # Skip if file already exists in DB
        if db.query(Document).filter(Document.filename == filename).first():
            continue

        text = extract_text(path)
        if not text:
            continue

        result = classify_document(text)
        try:
            data = json.loads(result)
        except:
            data = {"type": "OTHERS", "summary": "Invalid LLM output", "confidence": 0}

        doc = Document(
            filename=filename,
            doc_type=data["type"],
            summary=data["summary"],
            confidence=data["confidence"],
            source="crawl"
        )
        db.add(doc)
        new_files.append(filename)

    db.commit()

    return {"crawled": len(new_files), "files_added": new_files}


# ======================================================
# Get All Documents
# ======================================================

@app.get("/documents", response_model=list[DocumentResponse])
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
        }
        for d in docs
    ]


# ======================================================
# Get Document Detail
# ======================================================

@app.get("/documents/{id}", response_model=DocumentDetailResponse)
def get_document_detail(id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": doc.id,
        "filename": doc.filename,
        "doc_type": doc.doc_type,
        "summary": doc.summary,
        "confidence": doc.confidence,
        "source": doc.source,
        "created_at": doc.created_at.isoformat()
    }


# ======================================================
# Get Document Content (Extracted text)
# ======================================================

@app.get("/documents/{id}/content", response_model=DocumentContentResponse)
def get_document_content(id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = os.path.join("data/raw", doc.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on server")

    text = extract_text(file_path) or "Content not extractable"

    return {"document_id": doc.id, "content": text}


# ======================================================
# Download file (PDF or any file)
# ======================================================

@app.get("/documents/{id}/download")
def download_document(id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = os.path.join("data/raw", doc.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on server")

    return FileResponse(
        file_path,
        media_type="application/octet-stream",
        filename=doc.filename,
        headers={"Content-Disposition": f"attachment; filename={doc.filename}"}
    )


# ======================================================
# Categories
# ======================================================

@app.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    items = db.query(Category).all()
    return [{"key": c.key, "description": c.description} for c in items]


# ======================================================
# Stats
# ======================================================

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    docs = db.query(Document.doc_type).all()

    stats = {}
    for (t,) in docs:
        if t:
            stats[t] = stats.get(t, 0) + 1

    return {"stats": stats}
