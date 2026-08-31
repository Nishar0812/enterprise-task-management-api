from marshmallow import (
    EXCLUDE,
    RAISE,
    Schema,
    ValidationError,
    fields,
    pre_load,
    validate,
    validates_schema,
)

from app.models.task import PRIORITY_VALUES, STATUS_VALUES

TASK_SORT_VALUES = ("created_at", "updated_at", "title", "status", "priority")


def _normalize_title(data: dict) -> None:
    value = data.get("title")
    if isinstance(value, str):
        data["title"] = value.strip()


class TaskCreateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    title = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    description = fields.Str(load_default=None, allow_none=True)
    status = fields.Str(load_default="pending", validate=validate.OneOf(STATUS_VALUES))
    priority = fields.Str(
        load_default="medium", validate=validate.OneOf(PRIORITY_VALUES)
    )
    assigned_to = fields.Int(load_default=None, allow_none=True, strict=True)

    @pre_load
    def normalize(self, data, **kwargs):
        if not isinstance(data, dict):
            return data
        data = dict(data)
        _normalize_title(data)
        return data


class TaskUpdateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    title = fields.Str(validate=validate.Length(min=1, max=200))
    description = fields.Str(allow_none=True)
    status = fields.Str(validate=validate.OneOf(STATUS_VALUES))
    priority = fields.Str(validate=validate.OneOf(PRIORITY_VALUES))
    assigned_to = fields.Int(allow_none=True, strict=True)

    @pre_load
    def normalize(self, data, **kwargs):
        if not isinstance(data, dict):
            return data
        data = dict(data)
        _normalize_title(data)
        return data

    @validates_schema
    def require_at_least_one_field(self, data, **kwargs):
        if not data:
            raise ValidationError("At least one task field is required.")


class TaskSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int(dump_only=True)
    title = fields.Str(dump_only=True)
    description = fields.Str(dump_only=True, allow_none=True)
    status = fields.Str(dump_only=True)
    priority = fields.Str(dump_only=True)
    project_id = fields.Int(dump_only=True)
    assigned_to = fields.Int(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class TaskQuerySchema(Schema):
    class Meta:
        unknown = RAISE

    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    limit = fields.Int(load_default=20, validate=validate.Range(min=1, max=100))
    status = fields.Str(validate=validate.OneOf(STATUS_VALUES))
    priority = fields.Str(validate=validate.OneOf(PRIORITY_VALUES))
    assigned_to = fields.Int(validate=validate.Range(min=1))
    search = fields.Str(validate=validate.Length(min=1, max=200))
    sort = fields.Str(
        load_default="created_at", validate=validate.OneOf(TASK_SORT_VALUES)
    )
    order = fields.Str(load_default="desc", validate=validate.OneOf(("asc", "desc")))

    @pre_load
    def normalize_search(self, data, **kwargs):
        if not isinstance(data, dict):
            return data
        data = dict(data)
        if isinstance(data.get("search"), str):
            data["search"] = data["search"].strip()
        return data
