"""Legacy adapter aliases maintained for backward compatibility.

The refactor introduced ``chatbot.apps`` as the canonical home for service
entry points (orchestrator, gateway, ingestion worker). To avoid breaking
existing imports and entry commands we alias the old module paths to the new
locations. New code should import from ``chatbot.apps`` directly.
"""

from __future__ import annotations

from importlib import import_module
import sys
from types import ModuleType

_ALIASES = {
    "orchestrator": "chatbot.apps.orchestrator",
    "channel_gateway": "chatbot.apps.gateway",
    "gateway": "chatbot.apps.gateway",  # allow both spellings
    "ingestion": "chatbot.apps.ingestion",
}


def _alias(name: str, target: str) -> ModuleType:
    module = import_module(target)
    sys.modules[f"{__name__}.{name}"] = module
    return module


for alias, target in _ALIASES.items():
    _alias(alias, target)


__all__ = list(_ALIASES.keys())
