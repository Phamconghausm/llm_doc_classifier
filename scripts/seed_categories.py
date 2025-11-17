# scripts/seed_categories.py
from utils.db import SessionLocal, init_db, Category
from utils.category_mapping import CATEGORY_MAP

def seed():
    init_db()
    db = SessionLocal()
    try:
        for key, desc in CATEGORY_MAP.items():
            exists = db.query(Category).filter_by(key=key).first()
            if not exists:
                db.add(Category(key=key, description=desc))
        db.commit()
        print("Seed categories OK.")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
