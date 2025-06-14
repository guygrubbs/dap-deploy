"""
Central SQLAlchemy setup.

*   Reads DATABASE_URL from the environment.
*   Creates an Engine with sensible pooling + disconnect handling.
*   Exposes `SessionLocal()` factory and `Base` declarative metadata.
*   Provides `get_db()` FastAPI dependency + `init_db()` helper.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# --------------------------------------------------------------------------- #
# Environment
# --------------------------------------------------------------------------- #
DATABASE_URL: str | None = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set – cannot start application without a database."
    )

# --------------------------------------------------------------------------- #
# Engine
# --------------------------------------------------------------------------- #
# Docs: https://docs.sqlalchemy.org/en/latest/core/engines.html                 :contentReference[oaicite:0]{index=0}
# pool_pre_ping handles stale connections.                                     :contentReference[oaicite:1]{index=1}
ENGINE = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=1800,  # 30 min – keeps long-lived workers fresh.             :contentReference[oaicite:2]{index=2}
    echo=os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true",
    future=True,  # 2.0-style engine                                       :contentReference[oaicite:3]{index=3}
)

# --------------------------------------------------------------------------- #
# Session factory
# --------------------------------------------------------------------------- #
SessionLocal = sessionmaker(
    bind=ENGINE,
    expire_on_commit=False,  # typical for FastAPI
    autoflush=False,        # we control flush explicitly                      :contentReference[oaicite:4]{index=4}
    autocommit=False,
)

# --------------------------------------------------------------------------- #
# Declarative base
# --------------------------------------------------------------------------- #
Base = declarative_base()  # other modules import this for model definitions.  :contentReference[oaicite:5]{index=5}

# --------------------------------------------------------------------------- #
# Dependency helpers
# --------------------------------------------------------------------------- #
@contextmanager
def db_session() -> Generator[Session, None, None]:
    """
    Context-manager version::

        with db_session() as db:
            db.query(...)

    Closes and rolls back automatically on error.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    Create all tables that are imported into metadata.
    Call once at startup (or run Alembic migrations instead).
    """
    import app.database.models  # noqa: F401 – ensure models are imported

    Base.metadata.create_all(bind=ENGINE)
