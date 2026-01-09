from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.routes import auth, teacher, student, files
from app.db.base import Base
from app.db.session import engine
from app.db.init_db import seed_demo_data


settings = get_settings()

app = FastAPI(title=settings.project_name)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    seed_demo_data()

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router, tags=["auth"])
app.include_router(teacher.router, prefix="/teacher", tags=["teacher"])
app.include_router(student.router, prefix="/student", tags=["student"])
app.include_router(files.router, tags=["files"])
