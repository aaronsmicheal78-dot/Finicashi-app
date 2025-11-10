"""add phone column to withdrawals

Revision ID: e3b1b72a7ede
Revises: 70412d0fa9dd
Create Date: 2025-11-10 05:01:45.992655

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e3b1b72a7ede'
down_revision = '70412d0fa9dd'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass

def upgrade():
    with op.batch_alter_table('withdrawals') as batch_op:
        batch_op.add_column(sa.Column('phone', sa.String(length=20), nullable=True))

def downgrade():
    with op.batch_alter_table('withdrawals') as batch_op:
        batch_op.drop_column('phone')
