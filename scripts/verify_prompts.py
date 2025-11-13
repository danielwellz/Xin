#!/usr/bin/env python
"""Ensure backend/front-end prompt packs still include the required sections."""

from __future__ import annotations

from pathlib import Path

PROMPT_FILES = {
    Path("docs/MASTER_PROMPTS_HARDENING.md"): [f"Prompt {idx}" for idx in range(1, 6)],
}


def main() -> int:
    missing: list[str] = []
    for path, tokens in PROMPT_FILES.items():
        if not path.exists():
            missing.append(f"{path} (file missing)")
            continue
        text = path.read_text(encoding="utf-8")
        for token in tokens:
            if token not in text:
                missing.append(f"{path}: {token}")
    if missing:
        print("❌ Prompt verification failed. Missing sections:")
        for item in missing:
            print(f"  - {item}")
        return 1
    print("✅ Prompt packs verified (Prompts 1–5 present in both docs).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
