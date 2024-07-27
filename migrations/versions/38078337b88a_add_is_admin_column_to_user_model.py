"""Add is_admin column to User model

Revision ID: 38078337b88a
Revises: 31e86ed79b04
Create Date: 2024-07-15 03:18:51.348179

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '38078337b88a'
down_revision = '31e86ed79b04'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_admin', sa.Boolean(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('is_admin')

    # ### end Alembic commands ###