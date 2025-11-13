"""Contract tests to ensure admin API surfaces stay aligned with the frontend schemas."""

from __future__ import annotations

from pathlib import Path

from chatbot.admin import schemas as admin_schemas
from chatbot.core.domain import ChannelType

FRONTEND_SCHEMAS = Path("services/frontend/src/api/schemas.ts")


def test_type_tokens_exist_in_frontend() -> None:
    assert (
        FRONTEND_SCHEMAS.exists()
    ), "Frontend schema file missing; did you run git submodules?"
    ts_source = FRONTEND_SCHEMAS.read_text(encoding="utf-8")

    model_map = {
        "TenantResponse": "const TenantSchema",
        "ChannelResponse": "const ChannelSchema",
        "PolicyVersionResponse": "const PolicyVersionSchema",
        "PolicyDiffResponse": "const PolicyDiffSchema",
        "RetrievalConfigResponse": "const RetrievalConfigSchema",
        "KnowledgeAssetResponse": "const KnowledgeAssetSchema",
        "IngestionJobResponse": "const IngestionJobSchema",
        "AutomationRuleResponse": "const AutomationRuleSchema",
        "AutomationJobResponse": "const AutomationJobSchema",
    }

    for backend_model, frontend_token in model_map.items():
        assert hasattr(
            admin_schemas, backend_model
        ), f"{backend_model} missing in backend schemas"
        assert (
            frontend_token in ts_source
        ), f"{frontend_token} missing from services/frontend/src/api/schemas.ts (contract drift)"


def test_channel_type_enum_matches_frontend() -> None:
    ts_source = FRONTEND_SCHEMAS.read_text(encoding="utf-8")
    start_token = "export const ChannelTypeSchema = z.enum(["
    start_idx = ts_source.index(start_token) + len(start_token)
    end_idx = ts_source.index("])", start_idx)
    enum_literal = ts_source[start_idx:end_idx]
    frontend_values = {
        token.strip().strip('"').strip("'")
        for token in enum_literal.split(",")
        if token.strip()
    }
    backend_values = {channel_type.value for channel_type in ChannelType}
    assert (
        frontend_values == backend_values
    ), f"ChannelType mismatch: {frontend_values} != {backend_values}"
