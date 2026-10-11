import jsonschema
from django.core.exceptions import ValidationError

FIELD_CONFIG_SCHEMA = {
    "type": "object",
    "patternProperties": {
        "^[a-zA-Z0-9_]+$": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "minimum": 0},
                "y": {"type": "integer", "minimum": 0},
                "font_size": {"type": "integer", "minimum": 1},
                "font": {"type": "string"},
                "color": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"},
                "align": {"type": "string", "enum": ["left", "center", "right"]},
                "clear_background": {"type": "boolean"},
                "bg_color": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"},
                "mask_width": {"type": "integer", "minimum": 1},
                "mask_height": {"type": "integer", "minimum": 1}
            },
            "required": ["x", "y"],
            "additionalProperties": False
        }
    },
    "additionalProperties": False
}

def validate_field_configuration(value):
    try:
        jsonschema.validate(instance=value, schema=FIELD_CONFIG_SCHEMA)
    except jsonschema.exceptions.ValidationError as e:
        raise ValidationError(f"Invalid field configuration: {e.message}")
