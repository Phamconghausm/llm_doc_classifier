from utils.db import SessionLocal, Document

db = SessionLocal()
db.query(Document).delete()
db.commit()
db.close()

print("✔ All documents have been removed.")
