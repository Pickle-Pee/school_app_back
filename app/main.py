from fastapi import FastAPI

from app.api.routes import auth, teacher, student, files
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.project_name)

app.include_router(auth.router, tags=["auth"])
app.include_router(teacher.router, prefix="/teacher", tags=["teacher"])
app.include_router(student.router, prefix="/student", tags=["student"])
app.include_router(files.router, tags=["files"])
