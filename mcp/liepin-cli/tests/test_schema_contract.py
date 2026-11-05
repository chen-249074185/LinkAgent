import json
from pathlib import Path

from liepin_cli.models.registry import SCHEMA_MODEL_REGISTRY


SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"


def _load_schema(filename: str) -> dict:
    return json.loads((SCHEMAS_DIR / filename).read_text(encoding="utf-8"))


def _normalize_property_schema(property_schema: dict) -> tuple[str | None, str | None]:
    if "anyOf" in property_schema:
        variants = [item for item in property_schema["anyOf"] if item.get("type") != "null"]
        if len(variants) == 1:
            property_schema = variants[0]
    property_type = property_schema.get("type")
    item_type = None
    if property_type == "array":
        item_type = property_schema.get("items", {}).get("type")
    return property_type, item_type


def test_registry_covers_all_schema_files() -> None:
    schema_files = {path.name for path in SCHEMAS_DIR.glob("*.json")}
    assert set(SCHEMA_MODEL_REGISTRY) == schema_files


def test_model_fields_match_schema_properties() -> None:
    for filename, model_cls in SCHEMA_MODEL_REGISTRY.items():
        schema = _load_schema(filename)
        assert set(model_cls.model_fields) == set(schema["properties"])


def test_model_required_fields_match_schema_required() -> None:
    for filename, model_cls in SCHEMA_MODEL_REGISTRY.items():
        schema = _load_schema(filename)
        required_fields = {
            name for name, field in model_cls.model_fields.items() if field.is_required()
        }
        assert required_fields == set(schema.get("required", []))


def test_model_json_schema_matches_basic_schema_types() -> None:
    for filename, model_cls in SCHEMA_MODEL_REGISTRY.items():
        source_schema = _load_schema(filename)
        model_schema = model_cls.model_json_schema()
        for field_name, source_property in source_schema["properties"].items():
            model_property = model_schema["properties"][field_name]
            source_type, source_item_type = _normalize_property_schema(source_property)
            model_type, model_item_type = _normalize_property_schema(model_property)
            if source_type == "number":
                assert model_type in {"number", "integer"}
            else:
                assert model_type == source_type
            assert model_item_type == source_item_type
            if "enum" in source_property:
                assert model_property.get("enum") == source_property["enum"]
