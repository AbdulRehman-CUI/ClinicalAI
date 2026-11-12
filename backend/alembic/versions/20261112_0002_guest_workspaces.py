"""Add anonymous workspaces and encrypted LLM configuration."""

from alembic import op
import sqlalchemy as sa

revision = "20261112_0002"
down_revision = "20261112_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "guest_workspaces",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("credential_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("llm_rate_bucket", sa.Integer(), server_default="0", nullable=False),
        sa.Column("llm_rate_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_index("ix_guest_workspaces_expires_at", "guest_workspaces", ["expires_at"])
    op.create_table(
        "workspace_llm_configurations",
        sa.Column("workspace_id", sa.String(32), sa.ForeignKey("guest_workspaces.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=False),
        sa.Column("session_hash", sa.String(64)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_workspace_llm_configurations_expires_at", "workspace_llm_configurations", ["expires_at"])
    # Existing clinical data had no trustworthy per-visitor ownership.
    for table in ("patients", "report_storage_deletions"):
        if op.get_context().dialect.name == "sqlite":
            # SQLite allows adding a nullable foreign-key column inline.
            op.execute(f"ALTER TABLE {table} ADD COLUMN workspace_id VARCHAR(32) REFERENCES guest_workspaces(id)")
        else:
            op.add_column(table, sa.Column("workspace_id", sa.String(32), nullable=True))
            op.create_foreign_key(f"fk_{table}_workspace", table, "guest_workspaces", ["workspace_id"], ["id"])
        op.create_index(f"ix_{table}_workspace_id", table, ["workspace_id"])


def downgrade() -> None:
    raise RuntimeError("Restoring the pre-workspace schema would discard ownership and credentials. Restore a verified backup instead.")
