from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Any


@dataclass
class OperatorTemplate:
    id: int
    name: str
    qualified_process_types: set[str] = field(default_factory=set)


def default_operator_library_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "FactorySimulation" / "operator_library.json"
    return Path.home() / ".factory_simulation" / "operator_library.json"


def load_operator_templates(path: str | Path) -> list[OperatorTemplate]:
    source = Path(path)
    if not source.exists():
        return []

    data: Any = json.loads(source.read_text(encoding="utf-8"))
    raw_templates = data.get("operators", []) if isinstance(data, dict) else data
    if not isinstance(raw_templates, list):
        raise ValueError("Operator library must contain an operator list.")

    templates: list[OperatorTemplate] = []
    for item in raw_templates:
        if not isinstance(item, dict):
            raise ValueError("Operator library entries must be objects.")

        name = str(item.get("name", "")).strip()
        if not name:
            raise ValueError("Operator template name is required.")

        templates.append(
            OperatorTemplate(
                id=int(item["id"]),
                name=name,
                qualified_process_types=set(item.get("qualified_process_types", [])),
            )
        )

    return templates


def save_operator_templates(
    templates: list[OperatorTemplate],
    path: str | Path,
) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "operators": [
            {
                "id": template.id,
                "name": template.name,
                "qualified_process_types": sorted(template.qualified_process_types),
            }
            for template in templates
        ]
    }
    destination.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def upsert_operator_template(
    templates: list[OperatorTemplate],
    name: str,
    qualified_process_types: set[str] | list[str] | tuple[str, ...],
) -> tuple[OperatorTemplate, bool]:
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("Operator template name is required.")

    for template in templates:
        if template.name.casefold() == normalized_name.casefold():
            template.name = normalized_name
            template.qualified_process_types = set(qualified_process_types)
            return template, False

    next_id = max((template.id for template in templates), default=0) + 1
    template = OperatorTemplate(
        id=next_id,
        name=normalized_name,
        qualified_process_types=set(qualified_process_types),
    )
    templates.append(template)
    return template, True


def delete_operator_template(
    templates: list[OperatorTemplate],
    template_id: int,
) -> OperatorTemplate | None:
    for index, template in enumerate(templates):
        if template.id == template_id:
            return templates.pop(index)
    return None
