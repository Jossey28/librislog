from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logging_config import configure_logging
from app.routers import books, covers, import_

configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.covers_dir).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="LibrisLog API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(books.router)
app.include_router(import_.router)
app.include_router(covers.router)


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}
