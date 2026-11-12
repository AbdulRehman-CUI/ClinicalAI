"""Add idempotent report names and durable object deletion tracking."""

from alembic import context, op
import sqlalchemy as sa

revision = "20261112_0001"
down_revision = "20260803_0001"
branch_labels = None
depends_on = None

FILE_TYPE_CONSTRAINT = "ck_medical_reports_file_type"
LEGACY_FILE_TYPES = "file_type IN ('PDF', 'PNG', 'JPG', 'JPEG')"
CURRENT_FILE_TYPES = "file_type IN ('PDF', 'DOCX', 'TXT', 'PNG', 'JPG', 'JPEG')"


def upgrade() -> None:
    inspector = None if context.is_offline_mode() else sa.inspect(op.get_bind())
    # The initial migration allowed fewer types than the application model.
    if inspector is None or any(
        check["name"] == FILE_TYPE_CONSTRAINT and "DOCX" not in check["sqltext"]
        for check in inspector.get_check_constraints("medical_reports")
    ):
        replace_file_type_constraint(CURRENT_FILE_TYPES)
    if inspector is None or not inspector.has_table("report_storage_deletions"):
        op.create_table(
            "report_storage_deletions",
            sa.Column("stored_filename", sa.String(255), primary_key=True),
            sa.Column("report_id", sa.Integer(), nullable=False),
        )
        op.create_index("ix_report_storage_deletions_report_id", "report_storage_deletions", ["report_id"])
    if inspector is None or not any(
        index["name"] == "ix_medical_reports_stored_filename"
        for index in inspector.get_indexes("medical_reports")
    ):
        op.create_index("ix_medical_reports_stored_filename", "medical_reports", ["stored_filename"], unique=True)


def downgrade() -> None:
    if not context.is_offline_mode() and op.get_bind().scalar(
        sa.text("SELECT COUNT(*) FROM medical_reports WHERE file_type IN ('DOCX', 'TXT')")
    ):
        raise RuntimeError("Archive or migrate existing DOCX/TXT reports before downgrading.")
    op.drop_index("ix_medical_reports_stored_filename", table_name="medical_reports")
    op.drop_index("ix_report_storage_deletions_report_id", table_name="report_storage_deletions")
    op.drop_table("report_storage_deletions")
    replace_file_type_constraint(LEGACY_FILE_TYPES)


def replace_file_type_constraint(expression: str) -> None:
    with op.batch_alter_table("medical_reports") as batch:
        batch.drop_constraint(FILE_TYPE_CONSTRAINT, type_="check")
        batch.create_check_constraint(FILE_TYPE_CONSTRAINT, expression)
