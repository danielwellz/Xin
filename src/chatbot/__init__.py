"""Core package for the Xin chatbot platform."""

from __future__ import annotations

from pkgutil import extend_path

__all__ = ["__version__"]

__version__ = "0.1.0"

# Allow service-specific namespaces to extend the chatbot package.
__path__ = extend_path(__path__, __name__)

# ---------------------------------------------------------------------------
# Test helpers: ensure in-memory SQLite engines work across threads.
# ---------------------------------------------------------------------------
try:  # pragma: no cover - optional dependency patching
    from sqlalchemy.pool import StaticPool
    import sqlmodel
except Exception:  # pragma: no cover
    pass
else:
    _sqlmodel_create_engine = sqlmodel.create_engine

    def create_engine(url, *args, **kwargs):
        url_string = str(url)
        if url_string.startswith("sqlite://") and "poolclass" not in kwargs:
            connect_args = kwargs.setdefault("connect_args", {})
            connect_args.setdefault("check_same_thread", False)
            kwargs["poolclass"] = StaticPool
            if url_string == "sqlite://":
                url = "sqlite+pysqlite:///:memory:"
        return _sqlmodel_create_engine(url, *args, **kwargs)

    sqlmodel.create_engine = create_engine
