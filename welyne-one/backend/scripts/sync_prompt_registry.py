#!/usr/bin/env python
"""
Registre de prompts (§5.3) : synchronise /prompts/<agent>/<nom>@vN.md vers la
table prompt_versions au démarrage. Usage : python scripts/sync_prompt_registry.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal  # noqa: E402
from app.models.prompt_version import PromptVersion  # noqa: E402

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
PATTERN = re.compile(r"^(?P<name>.+)@(?P<version>v\d+)\.md$")


def main():
    db = SessionLocal()
    count = 0
    try:
        for agent_dir in PROMPTS_DIR.iterdir():
            if not agent_dir.is_dir():
                continue
            agent = agent_dir.name
            for f in agent_dir.glob("*.md"):
                m = PATTERN.match(f.name)
                if not m:
                    continue
                name, version = m.group("name"), m.group("version")
                existing = (
                    db.query(PromptVersion)
                    .filter_by(agent=agent, name=name, version=version)
                    .first()
                )
                template = f.read_text(encoding="utf-8")
                if existing:
                    existing.template = template
                else:
                    db.add(PromptVersion(agent=agent, name=name, version=version, template=template))
                count += 1
        db.commit()
        print(f"{count} prompt(s) synchronisé(s) vers prompt_versions.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
