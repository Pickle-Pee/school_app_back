import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models import Theory, User

router = APIRouter()


@router.get("/files/{theory_id}")
def download_theory_file(
    theory_id: int,
    db: Session = Depends(get_db),
):
    theory = db.query(Theory).filter(Theory.id == theory_id).first()
    if not theory or not theory.file_path:
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        theory.file_path,
        filename=os.path.basename(theory.file_path),
        media_type="application/octet-stream",
    )