from marshmallow import EXCLUDE, RAISE, Schema, fields, pre_load, validate

from app.models.user import ROLE_VALUES


def _normalize_str_field(data: dict, field: str, *, lower: bool = False) -> None:
    value = data.get(field)
    if isinstance(value, str):
        value = value.strip()
        if lower:
            value = value.lower()
        data[field] = value


class RegisterRequestSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.Str(required=True, validate=validate.Length(min=1, max=120))
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8), load_only=True)

    @pre_load
    def normalize(self, data, **kwargs):
        if not isinstance(data, dict):
            return data
        data = dict(data)
        _normalize_str_field(data, "name")
        _normalize_str_field(data, "email", lower=True)
        return data


class LoginRequestSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)

    @pre_load
    def normalize(self, data, **kwargs):
        if not isinstance(data, dict):
            return data
        data = dict(data)
        _normalize_str_field(data, "email", lower=True)
        return data


class UserSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int(dump_only=True)
    name = fields.Str(dump_only=True)
    email = fields.Email(dump_only=True)
    role = fields.Str(dump_only=True)


class RoleUpdateSchema(Schema):
    class Meta:
        unknown = RAISE

    role = fields.Str(required=True, validate=validate.OneOf(ROLE_VALUES))
