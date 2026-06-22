from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


class ParseError(Exception):
    pass


def detect_format(filename: str, content_type: str | None = None) -> str:
    ext = Path(filename).suffix.lower()
    mapping = {".csv": "csv", ".json": "json", ".xml": "xml"}
    if ext in mapping:
        return mapping[ext]
    if content_type:
        ct = content_type.lower()
        if "csv" in ct:
            return "csv"
        if "json" in ct:
            return "json"
        if "xml" in ct:
            return "xml"
    raise ParseError(f"Cannot detect file format for {filename!r}")


def parse_file(path: Path, file_format: str) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8-sig")
    if file_format == "csv":
        return parse_csv(text)
    if file_format == "json":
        return parse_json(text)
    if file_format == "xml":
        return parse_xml(text)
    raise ParseError(f"Unsupported format: {file_format!r}")


def parse_csv(text: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        raise ParseError("CSV file has no header row")
    return [dict(row) for row in reader]


def parse_json(text: str) -> list[dict[str, Any]]:
    data = json.loads(text)
    if isinstance(data, list):
        if not all(isinstance(item, dict) for item in data):
            raise ParseError("JSON array must contain objects")
        return data
    if isinstance(data, dict):
        for key in ("records", "data", "items", "accounts"):
            if key in data and isinstance(data[key], list):
                items = data[key]
                if not all(isinstance(item, dict) for item in items):
                    raise ParseError(f"JSON key {key!r} must contain objects")
                return items
        return [data]
    raise ParseError("JSON must be an object or array of objects")


def parse_xml(text: str) -> list[dict[str, Any]]:
    root = ET.fromstring(text)
    records: list[dict[str, Any]] = []

    # Prefer explicit <record> elements; fall back to direct children of root.
    elements = root.findall(".//record")
    if not elements:
        elements = list(root)

    for element in elements:
        if not isinstance(element.tag, str):
            continue
        record: dict[str, Any] = dict(element.attrib)
        for child in element:
            if isinstance(child.tag, str):
                record[child.tag] = (child.text or "").strip()
        if record:
            records.append(record)

    if not records:
        raise ParseError("XML contains no parseable records")
    return records
