"""empty message

Revision ID: 83e3d614d9a6
Revises: 9185f25654ab
Create Date: 2019-08-09 15:10:25.131639

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '83e3d614d9a6'
down_revision = '9185f25654ab'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('authorisation_code', sa.Column('used', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('authorisation_code', 'used')
    # ### end Alembic commands ###
