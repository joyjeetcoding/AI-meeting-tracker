from sqlmodel import SQLModel, create_engine, Session
from app.config import settings

# create_engine sets up the connection to SQLite
# check_same_thread=False is required for SQLite + FastAPI
# (FastAPI handles requests across multiple threads)
engine = create_engine(
    f"sqlite:///{settings.SQLITE_DB_PATH}",
    echo=False,     # set True to see raw SQL in logs (debugging)
    connect_args={"check_same_thread": False}
)

def create_db_and_tables():
    """Create all tables defined db_models.py(if they dont exists)"""
    SQLModel.metadata.create_all(engine)

def get_session():
    """
    Dependency for FastAPI routes.
    Yields a DB session, automatically closed after the request.

    Usage in a route:
        def my_route(session: Session = Depends(get_session)):
            ...
    """
    with Session(engine) as session:
        yield session