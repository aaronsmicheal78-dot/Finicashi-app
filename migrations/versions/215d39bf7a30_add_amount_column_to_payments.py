"""Add amount column to payments"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '215d39bf7a30'
down_revision = '5b37ca4b5130'  # whatever your previous revision is
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('payments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=True))
    op.execute("UPDATE payments SET amount = 0 WHERE amount IS NULL;")
    with op.batch_alter_table('payments', schema=None) as batch_op:
        batch_op.alter_column('amount', nullable=False)


def downgrade():
    with op.batch_alter_table('payments', schema=None) as batch_op:
        batch_op.drop_column('amount')
