"""Create documented database layer tables.

Revision ID: 20260728_0001
Revises:
Create Date: 2026-07-28
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260728_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create patient, clinical data, report, and AI analysis tables."""
    op.create_table(
        "patients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("biological_sex", sa.String(length=50), nullable=False),
        sa.Column("blood_group", sa.String(length=20), nullable=False),
        sa.Column("height_cm", sa.Float(), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=False),
        sa.Column("pregnancy_status", sa.String(length=50), nullable=True),
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
        sa.CheckConstraint("age > 0", name="ck_patients_age_positive"),
        sa.CheckConstraint("height_cm > 0", name="ck_patients_height_positive"),
        sa.CheckConstraint("weight_kg > 0", name="ck_patients_weight_positive"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patients_created_at", "patients", ["created_at"])

    op.create_table(
        "medical_histories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("condition_name", sa.String(length=255), nullable=False),
        sa.Column("diagnosis_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_medical_histories_patient_id",
        "medical_histories",
        ["patient_id"],
    )

    op.create_table(
        "medications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("medication_name", sa.String(length=255), nullable=False),
        sa.Column("dosage", sa.String(length=255), nullable=False),
        sa.Column("frequency", sa.String(length=255), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_medications_patient_id", "medications", ["patient_id"])

    op.create_table(
        "allergies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("allergen", sa.String(length=255), nullable=False),
        sa.Column("reaction", sa.String(length=255), nullable=False),
        sa.Column("severity", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_allergies_patient_id", "allergies", ["patient_id"])

    op.create_table(
        "symptoms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("symptom_name", sa.String(length=255), nullable=False),
        sa.Column("duration", sa.String(length=255), nullable=False),
        sa.Column("severity", sa.String(length=100), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_symptoms_patient_id", "symptoms", ["patient_id"])

    op.create_table(
        "medical_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=10), nullable=False),
        sa.Column(
            "upload_timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "file_type IN ('PDF', 'PNG', 'JPG', 'JPEG')",
            name="ck_medical_reports_file_type",
        ),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_medical_reports_patient_id", "medical_reports", ["patient_id"])
    op.create_index(
        "ix_medical_reports_upload_timestamp",
        "medical_reports",
        ["upload_timestamp"],
    )

    op.create_table(
        "ai_analyses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("medication_warnings", sa.JSON(), nullable=False),
        sa.Column("possible_diagnoses", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("supporting_evidence", sa.JSON(), nullable=False),
        sa.Column("missing_information", sa.JSON(), nullable=False),
        sa.Column("suggested_next_steps", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["report_id"], ["medical_reports.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_id", name="uq_ai_analyses_report_id"),
    )
    op.create_index("ix_ai_analyses_created_at", "ai_analyses", ["created_at"])
    op.create_index("ix_ai_analyses_patient_id", "ai_analyses", ["patient_id"])


def downgrade() -> None:
    """Drop documented database layer tables."""
    op.drop_index("ix_ai_analyses_patient_id", table_name="ai_analyses")
    op.drop_index("ix_ai_analyses_created_at", table_name="ai_analyses")
    op.drop_table("ai_analyses")

    op.drop_index("ix_medical_reports_upload_timestamp", table_name="medical_reports")
    op.drop_index("ix_medical_reports_patient_id", table_name="medical_reports")
    op.drop_table("medical_reports")

    op.drop_index("ix_symptoms_patient_id", table_name="symptoms")
    op.drop_table("symptoms")

    op.drop_index("ix_allergies_patient_id", table_name="allergies")
    op.drop_table("allergies")

    op.drop_index("ix_medications_patient_id", table_name="medications")
    op.drop_table("medications")

    op.drop_index("ix_medical_histories_patient_id", table_name="medical_histories")
    op.drop_table("medical_histories")

    op.drop_index("ix_patients_created_at", table_name="patients")
    op.drop_table("patients")

