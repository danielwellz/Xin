"""Exception hierarchy for channel gateway operations."""

from __future__ import annotations


class ChannelGatewayError(Exception):
    """Base exception for channel gateway failures."""


class SignatureVerificationError(ChannelGatewayError):
    """Raised when a webhook signature cannot be validated."""


class ProviderDispatchError(ChannelGatewayError):
    """Raised when outbound message dispatch to a provider fails."""
