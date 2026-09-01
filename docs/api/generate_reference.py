#!/usr/bin/env python3
"""Generate endpoint and schema Markdown from SocialN OpenAPI JSON."""

import argparse
import json
from pathlib import Path
from urllib.request import urlopen

METHODS = {"get", "post", "put", "patch", "delete"}


def load(source: str) -> dict:
    if source.startswith(("http://", "https://")):
        with urlopen(source, timeout=15) as response:
            return json.load(response)
    with open(source, encoding="utf-8") as handle:
        return json.load(handle)


def schema_name(schema: dict | None) -> str:
    schema = schema or {}
    if "$ref" in schema:
        return schema["$ref"].rsplit("/", 1)[-1]
    if "allOf" in schema:
        return " + ".join(schema_name(item) for item in schema["allOf"])
    if "anyOf" in schema:
        names = [schema_name(item) for item in schema["anyOf"] if item.get("type") != "null"]
        return " | ".join(names) or "any"
    if "oneOf" in schema:
        return " | ".join(schema_name(item) for item in schema["oneOf"])
    if schema.get("type") == "array":
        return f"{schema_name(schema.get('items'))}[]"
    return schema.get("type", "object")


def escape(value) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def endpoint_markdown(spec: dict) -> str:
    grouped = {}
    for path, path_item in spec["paths"].items():
        for method, operation in path_item.items():
            if method not in METHODS:
                continue
            tag = (operation.get("tags") or ["Other"])[0]
            grouped.setdefault(tag, []).append((path, method, operation))

    count = sum(map(len, grouped.values()))
    lines = [
        "# SocialN API — Danh mục endpoint", "",
        f"> Sinh từ OpenAPI {spec['info']['version']}. Tổng cộng **{count} REST operations** "
        f"trên **{len(spec['paths'])} paths**.", "",
        "Quy ước: **Có** trong cột Auth nghĩa là gửi `Authorization: Bearer {{token}}`. "
        "`Input` liệt kê path/query/header và request body.", "",
    ]
    for tag in sorted(grouped):
        lines += [f"## {tag}", "", "| Method | Endpoint | Auth | Input | Success |", "|---|---|:---:|---|---|"]
        for path, method, operation in sorted(grouped[tag], key=lambda item: (item[0], item[1])):
            inputs = []
            for parameter in operation.get("parameters", []):
                required = "*" if parameter.get("required") else ""
                inputs.append(
                    f"{parameter.get('in')} `{parameter.get('name')}`{required}: "
                    f"{schema_name(parameter.get('schema'))}"
                )
            for mime, details in operation.get("requestBody", {}).get("content", {}).items():
                inputs.append(f"body {mime}: `{schema_name(details.get('schema'))}`")
            success = ", ".join(
                f"`{code}`" for code in operation.get("responses", {}) if code.startswith("2")
            ) or "—"
            summary = operation.get("summary")
            endpoint = f"`{path}`" + (f"<br><small>{escape(summary)}</small>" if summary else "")
            lines.append(
                f"| `{method.upper()}` | {endpoint} | {'Có' if operation.get('security') else 'Không'} | "
                f"{escape('; '.join(inputs) or '—')} | {success} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def schema_markdown(spec: dict) -> str:
    schemas = spec.get("components", {}).get("schemas", {})
    lines = [
        "# SocialN API — Data schemas", "",
        f"> Data dictionary sinh từ OpenAPI. Tổng cộng **{len(schemas)} schemas**. "
        "Trường có dấu `*` là bắt buộc.", "",
    ]
    for name, schema in sorted(schemas.items()):
        lines += [f"## `{name}`", ""]
        if schema.get("description"):
            lines += [schema["description"], ""]
        properties = schema.get("properties", {})
        if not properties:
            lines += [f"Kiểu: `{schema_name(schema)}`", ""]
            continue
        required = set(schema.get("required", []))
        lines += [
            "| Field | Type | Required | Validation / default / description |",
            "|---|---|:---:|---|",
        ]
        for field, details in properties.items():
            metadata = []
            if "default" in details:
                metadata.append(f"default={details['default']!r}")
            if "enum" in details:
                metadata.append("enum: " + ", ".join(map(str, details["enum"])))
            for key in ("minLength", "maxLength", "minimum", "maximum", "pattern", "format"):
                if key in details:
                    metadata.append(f"{key}={details[key]}")
            if details.get("description"):
                metadata.append(details["description"])
            lines.append(
                f"| `{field}` | `{escape(schema_name(details))}` | "
                f"{'Có' if field in required else 'Không'} | {escape('; '.join(metadata) or '—')} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", nargs="?", default="http://localhost:8000/openapi.json")
    parser.add_argument("--output", default=str(Path(__file__).parent))
    args = parser.parse_args()
    spec = load(args.source)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "endpoints.md").write_text(endpoint_markdown(spec), encoding="utf-8")
    (output / "schemas.md").write_text(schema_markdown(spec), encoding="utf-8")
    print(f"Generated {output / 'endpoints.md'} and {output / 'schemas.md'}")


if __name__ == "__main__":
    main()
