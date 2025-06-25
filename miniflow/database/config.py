# config.py

USE_SQLITE = True
SQLITE_PATH = "miniflow.db"
POSTGRES_URL = "postgresql://miniflow_user:1234@localhost:5432/miniflow"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from contextlib import contextmanager

Base = declarative_base()

class DatabaseConfig:
    def __init__(self, db_path_or_url=None):
        if db_path_or_url is None:
            db_path_or_url = SQLITE_PATH if USE_SQLITE else POSTGRES_URL

        if USE_SQLITE:
            db_url = db_path_or_url if db_path_or_url.startswith("sqlite:///") else f"sqlite:///{db_path_or_url}"
            self.engine = create_engine(db_url, connect_args={"check_same_thread": False})
        else:
            db_url = db_path_or_url if db_path_or_url.startswith("postgresql://") else f"postgresql://{db_path_or_url}"
            self.engine = create_engine(db_url)

        self.Session = scoped_session(sessionmaker(bind=self.engine))

    def get_engine(self):
        return self.engine

    def get_session(self):
        return self.Session


@contextmanager
def DatabaseConnection(db_path_or_url=None):
    config = DatabaseConfig(db_path_or_url)
    session = config.get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
