from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class DuplicateJsonKeyError(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonKeyError(f"Duplicate JSON object key: {key}")
        result[key] = value
    return result


def loads_json_strict(value: str, *, source: str = "JSON input") -> Any:
    try:
        return json.loads(value, object_pairs_hook=_unique_object)
    except (json.JSONDecodeError, DuplicateJsonKeyError) as exc:
        raise ValueError(f"Invalid {source}: {exc}") from exc


def load_json_strict(path: Path) -> Any:
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    return loads_json_strict(path.read_text(encoding="utf-8"), source=str(path))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reject malformed JSON and duplicate object keys."
    )
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    for path in args.paths:
        load_json_strict(path)
    print(
        json.dumps(
            {"validated": [str(path.resolve()) for path in args.paths]}, indent=2
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
