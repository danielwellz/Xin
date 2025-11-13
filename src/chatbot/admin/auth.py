"""Minimal JWT utilities tailored for the admin surface."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any, Sequence
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError


class TokenValidationError(Exception):
    """Raised when a token is malformed or fails verification."""


class TokenClaims(BaseModel):
    """Normalized view over the JWT payload."""

    sub: str
    iss: str
    aud: str
    exp: int
    iat: int
    roles: list[str] = Field(default_factory=list)
    tenant_id: UUID | None = None

    def has_scope(self, scope: str) -> bool:
        return scope in self.roles


@dataclass(slots=True)
class JWTService:
    """Very small HS256 JWT implementation to avoid extra dependencies."""

    secret: str
    issuer: str
    audience: str
    ttl_seconds: int

    def issue_token(
        self,
        *,
        subject: str,
        roles: Sequence[str],
        tenant_id: UUID | None = None,
        ttl_override_seconds: int | None = None,
    ) -> str:
        issued_at = int(time.time())
        ttl = ttl_override_seconds or self.ttl_seconds
        payload = {
            "sub": subject,
            "iss": self.issuer,
            "aud": self.audience,
            "iat": issued_at,
            "exp": issued_at + ttl,
            "roles": list(roles),
        }
        if tenant_id:
            payload["tenant_id"] = str(tenant_id)

        header = {"alg": "HS256", "typ": "JWT"}
        signing_input = ".".join(
            (
                _b64_encode(
                    json.dumps(header, separators=(",", ":"), sort_keys=True).encode(
                        "utf-8"
                    )
                ),
                _b64_encode(
                    json.dumps(payload, separators=(",", ":"), sort_keys=True).encode(
                        "utf-8"
                    )
                ),
            )
        )
        signature = self._sign(signing_input.encode("utf-8"))
        return f"{signing_input}.{signature}"

    def validate_token(self, token: str) -> TokenClaims:
        try:
            header_b64, payload_b64, signature = token.split(".")
        except ValueError as exc:  # pragma: no cover - sanity guard
            raise TokenValidationError("token structure invalid") from exc

        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = self._sign(signing_input)
        if not hmac.compare_digest(signature, expected_sig):
            raise TokenValidationError("token signature invalid")

        payload_bytes = _b64_decode(payload_b64)
        try:
            payload = json.loads(payload_bytes.decode("utf-8"))
        except json.JSONDecodeError as exc:  # pragma: no cover
            raise TokenValidationError("token payload invalid") from exc

        now = int(time.time())
        if payload.get("iss") != self.issuer:
            raise TokenValidationError("issuer mismatch")
        if payload.get("aud") != self.audience:
            raise TokenValidationError("audience mismatch")
        if now >= int(payload.get("exp", 0)):
            raise TokenValidationError("token expired")

        try:
            return TokenClaims.model_validate(payload)
        except ValidationError as exc:
            raise TokenValidationError("token payload malformed") from exc

    def _sign(self, data: bytes) -> str:
        digest = hmac.new(self.secret.encode("utf-8"), data, hashlib.sha256).digest()
        return _b64_encode(digest)


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
