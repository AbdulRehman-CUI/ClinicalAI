"""Preserve existing ciphertext, expiry, session binding and active selection."""
from alembic import op
import sqlalchemy as sa
revision = "20261120_0001"
down_revision = "20261112_0002"
branch_labels = depends_on = None

def upgrade():
    op.create_table("workspace_llm_configurations_new",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("workspace_id", sa.String(32), sa.ForeignKey("guest_workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("base_url", sa.String(2048)),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=False),
        sa.Column("session_hash", sa.String(64)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))
    op.execute("INSERT INTO workspace_llm_configurations_new (id, workspace_id, active, provider, model, encrypted_api_key, session_hash, expires_at) SELECT workspace_id, workspace_id, true, provider, model, encrypted_api_key, session_hash, expires_at FROM workspace_llm_configurations")
    op.drop_table("workspace_llm_configurations")
    op.rename_table("workspace_llm_configurations_new", "workspace_llm_configurations")
    op.create_index("ix_workspace_llm_configurations_workspace_id", "workspace_llm_configurations", ["workspace_id"])
    op.create_index("ix_workspace_llm_configurations_expires_at", "workspace_llm_configurations", ["expires_at"])
    op.create_index("uq_workspace_active_llm", "workspace_llm_configurations", ["workspace_id"], unique=True, postgresql_where=sa.text("active"), sqlite_where=sa.text("active = 1"))

def downgrade():
    raise RuntimeError("Multiple credentials cannot be downgraded losslessly. Restore a verified backup.")
