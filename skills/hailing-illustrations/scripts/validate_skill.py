#!/usr/bin/env python3
"""Validate the hailing-illustrations skill package without external dependencies."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "SKILL.md",
    "agents/openai.yaml",
    "references/style-dna.md",
    "references/hailing-ip.md",
    "references/composition-patterns.md",
    "references/prompt-template.md",
    "references/shot-list-template.md",
    "references/qa-checklist.md",
    "assets/character/hailing-normal-three-view.png",
    "assets/character/hailing-chibi-three-view.png",
    "assets/character/hailing-character-sheet.png",
    "assets/examples/01-hailing-odoo-tutorial.png",
    "assets/examples/02-hailing-skill-overview.png",
    "assets/icon-small.png",
    "assets/icon-large.png",
    "LICENSE",
    "NOTICE.md",
]

FORBIDDEN = [
    "xiaohei",
    "ian-xiaohei",
    "lan xiaohei",
    "罗小黑",
    "小黑",
]


def fail(message: str) -> None:
    print(f"[FAIL] {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    missing = [rel for rel in REQUIRED if not (ROOT / rel).is_file()]
    if missing:
        fail("missing required files: " + ", ".join(missing))

    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    if not skill.startswith("---\n"):
        fail("SKILL.md must start with YAML front matter")

    front = skill.split("---", 2)[1]
    name_match = re.search(r"(?m)^name:\s*([^\n]+)$", front)
    description_match = re.search(r"(?m)^description:\s*([^\n]+)$", front)
    if not name_match or name_match.group(1).strip() != "hailing-illustrations":
        fail("SKILL.md name must be hailing-illustrations")
    if not description_match or len(description_match.group(1).strip()) < 30:
        fail("SKILL.md description is missing or too short")

    agent_yaml = (ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
    for token in ["display_name:", "short_description:", "default_prompt:", "$hailing-illustrations"]:
        if token not in agent_yaml:
            fail(f"agents/openai.yaml missing {token}")

    text_paths = list(ROOT.rglob("*.md")) + list(ROOT.rglob("*.yaml")) + [ROOT / "VERSION"]
    # NOTICE and LICENSE may describe attribution; operational files must contain no old character names.
    operational = [p for p in text_paths if p.name not in {"NOTICE.md", "LICENSE"}]
    hits: list[str] = []
    for path in operational:
        text = path.read_text(encoding="utf-8").lower()
        for term in FORBIDDEN:
            if term.lower() in text:
                hits.append(f"{path.relative_to(ROOT)}: {term}")
    if hits:
        fail("old-character references remain: " + "; ".join(hits))

    for rel in REQUIRED:
        path = ROOT / rel
        if path.suffix.lower() == ".png" and path.stat().st_size < 10_000:
            fail(f"image asset appears invalid or too small: {rel}")

    for ref in re.findall(r"`((?:references|assets)/[^`]+)`", skill):
        if not (ROOT / ref).exists():
            fail(f"SKILL.md references missing path: {ref}")

    print("[PASS] hailing-illustrations skill package is valid")
    print(f"[PASS] root: {ROOT}")
    print(f"[PASS] required files: {len(REQUIRED)}")


if __name__ == "__main__":
    main()
