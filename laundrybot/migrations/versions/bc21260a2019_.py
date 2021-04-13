"""empty message

Revision ID: bc21260a2019
Revises: 80c9e5d762fa
Create Date: 2021-04-13 14:45:07.208493

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bc21260a2019'
down_revision = '80c9e5d762fa'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('load', sa.Column('last_change_time', sa.DateTime(), nullable=False))
    op.drop_column('load', 'cycle_number')
    op.add_column('roommate', sa.Column('telegram_id', sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('roommate', 'telegram_id')
    op.add_column('load', sa.Column('cycle_number', sa.INTEGER(), nullable=False))
    op.drop_column('load', 'last_change_time')
    # ### end Alembic commands ###
