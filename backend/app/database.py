import atexit
from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # needed for SQLite
)


@atexit.register
def _dispose_engine() -> None:
    """Ensure the engine pool is disposed on process exit to avoid ResourceWarnings."""
    engine.dispose()


def create_db_and_tables() -> None:
    """Create all database tables defined by SQLModel metadata."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Yield a SQLModel Session for the lifespan of the request."""
    with Session(engine) as session:
        yield session
