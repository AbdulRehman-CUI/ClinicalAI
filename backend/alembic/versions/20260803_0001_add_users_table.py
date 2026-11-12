"""Create the users table for authentication.

Revision ID: 20260803_0001
Revises: 20260728_0001
Create Date: 2026-08-03
"""

from __future__ import annotations

from alembic import context, op
import sqlalchemy as sa

revision = "20260803_0001"
down_revision = "20260728_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the users table if it does not already exist."""
    if not context.is_offline_mode() and sa.inspect(op.get_bind()).has_table("users"):
        return

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_created_at", "users", ["created_at"])
    op.create_index("ix_users_email", "users", ["email"])


def downgrade() -> None:
    """Drop the users table if it exists."""
    if not context.is_offline_mode() and not sa.inspect(op.get_bind()).has_table("users"):
        return

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_created_at", table_name="users")
    op.drop_table("users")
