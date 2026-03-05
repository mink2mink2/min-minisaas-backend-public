"""Add PDF domain - file management and conversion

Revision ID: 20260215_0003
Revises: 20260215_0002
Create Date: 2026-02-15 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic
revision = '20260215_0003'
down_revision = '20260215_0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create PDF domain tables"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("pdf_files"):
        return

    # Create pdf_files table (using text columns for enum-like behavior)
    op.create_table(
        'pdf_files',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('file_id', sa.String(100), nullable=False, unique=True),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('file_type', sa.String(20), nullable=False, server_default='pdf'),
        sa.Column('status', sa.String(20), nullable=False, server_default='uploading'),
        sa.Column('minio_bucket', sa.String(100), nullable=False),
        sa.Column('minio_path', sa.String(500), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column('output_path', sa.String(500), nullable=True),
        sa.Column('conversion_result', sa.Text(), nullable=True),
        sa.Column('conversion_cost', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('processed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('file_id'),
    )

    # Create indexes
    op.create_index('ix_pdf_files_user_id', 'pdf_files', ['user_id'])
    op.create_index('ix_pdf_files_file_id', 'pdf_files', ['file_id'])
    op.create_index('ix_pdf_files_status', 'pdf_files', ['status'])
    op.create_index('ix_pdf_files_created_at', 'pdf_files', ['created_at'])

    # Add check constraints for valid values
    op.execute("""
        ALTER TABLE pdf_files
        ADD CONSTRAINT check_file_type
        CHECK (file_type IN ('pdf', 'image', 'document'))
    """)

    op.execute("""
        ALTER TABLE pdf_files
        ADD CONSTRAINT check_status
        CHECK (status IN ('uploading', 'uploaded', 'processing', 'processed', 'failed', 'deleted'))
    """)


def downgrade() -> None:
    """Drop PDF domain tables"""
    op.drop_index('ix_pdf_files_created_at', table_name='pdf_files')
    op.drop_index('ix_pdf_files_status', table_name='pdf_files')
    op.drop_index('ix_pdf_files_file_id', table_name='pdf_files')
    op.drop_index('ix_pdf_files_user_id', table_name='pdf_files')
    op.drop_table('pdf_files')
