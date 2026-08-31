"""add task project created id index

Revision ID: 7c8d9e0f1a2b
Revises: 04e25d04f24a
Create Date: 2026-08-31

"""
from alembic import op


revision = "7c8d9e0f1a2b"
down_revision = "04e25d04f24a"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("tasks", schema=None) as batch_op:
        batch_op.create_index(
            "ix_tasks_project_created_id",
            ["project_id", "created_at", "id"],
            unique=False,
        )


def downgrade():
    with op.batch_alter_table("tasks", schema=None) as batch_op:
        batch_op.drop_index("ix_tasks_project_created_id")
