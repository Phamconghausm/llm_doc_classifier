# utils/db.py
import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_DIR = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DB_DIR, "documents.db")

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False, index=True)   # e.g. FINANCE_ACCOUNTING
    description = Column(Text)


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False, index=True)
    doc_type = Column(String)   # store category key (e.g. FINANCE_ACCOUNTING)
    summary = Column(Text)
    confidence = Column(Integer)
    source = Column(String, default="manual")
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    Base.metadata.create_all(bind=engine)
