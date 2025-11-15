"""add payment_type column in payments

Revision ID: bf86d88f2391
Revises: a35b4a42e920
Create Date: 2025-11-14 02:21:02.982694

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bf86d88f2391'
down_revision = 'a35b4a42e920'
branch_labels = None
depends_on = None


def upgrade():
    # Step 1 — Add column as nullable first
    with op.batch_alter_table('payments', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('payment_type', sa.String(length=50), nullable=True)
        )

    # Step 2 — Set default value for existing rows
    op.execute("UPDATE payments SET payment_type = 'package' WHERE payment_type IS NULL")

    # Step 3 — Now enforce NOT NULL
    with op.batch_alter_table('payments', schema=None) as batch_op:
        batch_op.alter_column('payment_type', nullable=False)


def downgrade():
    with op.batch_alter_table('payments', schema=None) as batch_op:
        batch_op.drop_column('payment_type')
