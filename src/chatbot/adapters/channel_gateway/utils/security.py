"""Security and signature verification helpers for provider webhooks."""

from __future__ import annotations

import base64
import hashlib
import hmac

from ..models import SignatureContext
from .exceptions import SignatureVerificationError


def validate_hmac_signature(context: SignatureContext, *, algorithm: str = "sha256") -> None:
    """Validate a provider webhook request using HMAC signatures."""

    secret = context.secret.encode("utf-8")
    payload = context.payload

    try:
        digestmod = getattr(hashlib, algorithm)
    except AttributeError as exc:  # pragma: no cover - safety guard
        raise SignatureVerificationError(f"unsupported hash algorithm: {algorithm}") from exc

    computed = hmac.new(secret, payload, digestmod=digestmod).hexdigest()
    if not hmac.compare_digest(computed, context.signature):
        raise SignatureVerificationError("signature mismatch")


def validate_sha1_signature(context: SignatureContext) -> None:
    """Validate signatures expressed as sha1= digest strings."""

    secret = context.secret.encode("utf-8")
    payload = context.payload
    signature = context.signature

    if signature.startswith("sha1="):
        signature = signature.split("=", 1)[1]

    computed = hmac.new(secret, payload, hashlib.sha1).hexdigest()
    if not hmac.compare_digest(computed, signature):
        raise SignatureVerificationError("signature mismatch")


def validate_base64_signature(context: SignatureContext) -> None:
    """Validate base64-encoded HMAC signatures."""

    secret = context.secret.encode("utf-8")
    payload = context.payload

    computed = hmac.new(secret, payload, hashlib.sha256).digest()
    expected = base64.b64decode(context.signature)

    if not hmac.compare_digest(computed, expected):
        raise SignatureVerificationError("signature mismatch")
