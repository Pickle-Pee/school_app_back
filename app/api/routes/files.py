import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import Theory

router = APIRouter()


@router.get("/files/{theory_id}")
def get_theory_file(theory_id: int, db: Session = Depends(get_db)):
    theory = db.query(Theory).filter(Theory.id == theory_id).first()
    if not theory or not theory.file_path:
        raise HTTPException(status_code=404, detail="File not found")
    if not os.path.exists(theory.file_path):
        raise HTTPException(status_code=404, detail="File missing on disk")
    return FileResponse(theory.file_path)
