"""SQLAlchemy engine and per-request session lifecycle."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, URL, make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

if TYPE_CHECKING:
    from pyramid.request import Request

    from palms_api.config import Settings


class Database:
    """Own one SQLAlchemy engine and create isolated request sessions."""

    def __init__(self, settings: Settings) -> None:
        self.url: URL = make_url(settings.database_url)
        self.engine = self._create_engine(settings)
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )

    def _create_engine(self, settings: Settings) -> Engine:
        options: dict[str, Any] = {
            "echo": settings.database_echo,
            "pool_pre_ping": not self.is_sqlite,
        }
        if self.is_sqlite:
            options["connect_args"] = {"check_same_thread": False}
            if self.url.database == ":memory:":
                # One shared in-memory database keeps the test connection safe
                # across SQLAlchemy sessions and Pyramid request boundaries.
                options["poolclass"] = StaticPool
        else:
            options["pool_size"] = settings.database_pool_size
            options["max_overflow"] = settings.database_max_overflow

        return create_engine(self.url, **options)

    @property
    def is_sqlite(self) -> bool:
        return self.url.get_backend_name() == "sqlite"

    def session_for_request(self, request: Request) -> Session:
        """Create a lazy request-scoped session and always clean it up."""
        session = self.session_factory()
        request.add_finished_callback(lambda _: self._close_session(session))
        return session

    @staticmethod
    def _close_session(session: Session) -> None:
        # This foundation has no write endpoints. Rolling back by default prevents
        # uncommitted future work from leaking between requests.
        try:
            session.rollback()
        finally:
            session.close()

    def check_connection(self) -> bool:
        """Return database availability without exposing driver exceptions."""
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception:
            return False
        return True

    def dispose(self) -> None:
        """Release the pool when a worker process is shutting down."""
        self.engine.dispose()
