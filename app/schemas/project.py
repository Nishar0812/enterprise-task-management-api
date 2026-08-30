from marshmallow import EXCLUDE, Schema, ValidationError, fields, pre_load, validate, validates_schema


def _normalize_name(data: dict) -> None:
    value = data.get("name")
    if isinstance(value, str):
        data["name"] = value.strip()


class ProjectCreateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.Str(required=True, validate=validate.Length(min=1, max=150))
    description = fields.Str(load_default=None, allow_none=True)

    @pre_load
    def normalize(self, data, **kwargs):
        if not isinstance(data, dict):
            return data
        data = dict(data)
        _normalize_name(data)
        return data


class ProjectUpdateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.Str(validate=validate.Length(min=1, max=150))
    description = fields.Str(allow_none=True)

    @pre_load
    def normalize(self, data, **kwargs):
        if not isinstance(data, dict):
            return data
        data = dict(data)
        _normalize_name(data)
        return data

    @validates_schema
    def require_at_least_one_field(self, data, **kwargs):
        if not data:
            raise ValidationError("At least one of 'name' or 'description' is required.")


class ProjectSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int(dump_only=True)
    name = fields.Str(dump_only=True)
    description = fields.Str(dump_only=True, allow_none=True)
    owner_id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
