"""Shared exception hierarchy for services."""

from __future__ import annotations

from collections.abc import Mapping
from http import HTTPStatus
from typing import Any


class CoreError(Exception):
    """Base exception capturing rich problem details."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
        code: str = "core_error",
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = int(status_code)
        self.code = code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """FastAPI/JSON-serializable representation of the error."""

        payload: dict[str, Any] = {
            "type": f"https://docs.example.com/errors/{self.code}",
            "title": self.message,
            "status": self.status_code,
            "code": self.code,
        }
        if self.details:
            payload["details"] = self.details
        return payload


class NotFoundError(CoreError):
    """Raised when a resource cannot be located."""

    def __init__(self, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            status_code=HTTPStatus.NOT_FOUND,
            code="not_found",
            details=details,
        )


class ValidationError(CoreError):
    """Raised when an upstream request fails validation."""

    def __init__(
        self,
        message: str,
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            code="validation_error",
            details=details,
        )


class UnauthorizedError(CoreError):
    """Raised when authentication fails or is missing."""

    def __init__(self, message: str = "unauthorized") -> None:
        super().__init__(
            message=message,
            status_code=HTTPStatus.UNAUTHORIZED,
            code="unauthorized",
        )


class ConflictError(CoreError):
    """Raised when a request conflicts with existing state."""

    def __init__(
        self,
        message: str,
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=HTTPStatus.CONFLICT,
            code="conflict",
            details=details,
        )
