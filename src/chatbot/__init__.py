"""Core package for the Xin chatbot platform."""

from __future__ import annotations

from pkgutil import extend_path

__all__ = ["__version__"]

__version__ = "0.1.0"

# Allow service-specific namespaces to extend the chatbot package.
__path__ = extend_path(__path__, __name__)
