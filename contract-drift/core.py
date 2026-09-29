"""SPDX-License-Identifier: MIT. Conservative request-contract compatibility checks."""
import json

TYPES = {"object", "array", "string", "integer", "number", "boolean", "null"}


def validate_schema(schema, depth=0):
    if depth > 20 or type(schema) is not dict:
        raise ValueError("Schema must be an object of depth <=20")
    supported = {"type", "properties", "required", "additionalProperties", "items", "enum", "description"}
    if set(schema) - supported:
        raise ValueError("Unsupported schema keywords: " + ", ".join(sorted(set(schema) - supported)))
    if not isinstance(schema.get("type"), str) or schema["type"] not in TYPES:
        raise ValueError("Explicit supported type is required")
    if "enum" in schema:
        if not isinstance(schema["enum"], list) or not schema["enum"]:
            raise ValueError("enum must be a nonempty array")
        for value in schema["enum"]:
            json.dumps(value, allow_nan=False)
    if schema["type"] == "object":
        props, required = schema.get("properties", {}), schema.get("required", [])
        if not isinstance(props, dict) or not isinstance(required, list) or any(not isinstance(k, str) for k in required):
            raise ValueError("Invalid object properties or required list")
        if set(required) - set(props) or len(set(required)) != len(required):
            raise ValueError("Required fields must be unique and declared")
        if type(schema.get("additionalProperties", True)) is not bool:
            raise ValueError("additionalProperties must be boolean")
        for child in props.values():
            validate_schema(child, depth + 1)
    elif any(k in schema for k in ("properties", "required", "additionalProperties")):
        raise ValueError("Object keywords on a non-object")
    if schema["type"] == "array":
        validate_schema(schema.get("items"), depth + 1)
    elif "items" in schema:
        raise ValueError("items on a non-array")


def compare(before, after):
    validate_schema(before)
    validate_schema(after)
    changes = []
    def add(path, reason, breaking):
        changes.append({"path": path, "reason": reason, "breaking": breaking})
    def walk(old, new, path):
        if old["type"] != new["type"]:
            widened = old["type"] == "integer" and new["type"] == "number"
            add(path, f'Type changed: {old["type"]} → {new["type"]}', not widened)
            if not widened:
                return
        if "enum" in new:
            encode = lambda value: json.dumps(value, sort_keys=True, allow_nan=False)
            current = {encode(v) for v in new["enum"]}
            previous = {encode(v) for v in old.get("enum", [])}
            if "enum" not in old or previous - current:
                add(path, "Accepted enum values narrowed", True)
        if old["type"] == "object":
            op, np = old.get("properties", {}), new.get("properties", {})
            for key in sorted(set(new.get("required", [])) - set(old.get("required", []))):
                add(path + "/" + key, "New required field", True)
            if old.get("additionalProperties", True) and not new.get("additionalProperties", True):
                add(path, "Additional properties are now forbidden", True)
            for key in sorted(set(op) - set(np)):
                add(path + "/" + key, "Declared field removed", not new.get("additionalProperties", True))
            for key in sorted(set(np) - set(op)):
                # Adding a constraint to an already accepted arbitrary property can break old requests.
                add(path + "/" + key, "Field added", old.get("additionalProperties", True))
            for key in sorted(set(op) & set(np)):
                walk(op[key], np[key], path + "/" + key)
        elif old["type"] == "array":
            walk(old["items"], new["items"], path + "/items")
    walk(before, after, "$")
    return {"compatible": not any(c["breaking"] for c in changes), "changes": changes,
            "direction": "Old requests accepted by the new request schema; conservative subset only"}
