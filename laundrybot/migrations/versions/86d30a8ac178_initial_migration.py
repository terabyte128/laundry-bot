"""Initial migration

Revision ID: 86d30a8ac178
Revises: 
Create Date: 2021-04-04 22:58:23.382980

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '86d30a8ac178'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('machine',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('last_reading', sa.Float(), nullable=False),
    sa.Column('updated_at', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('load',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('machine_id', sa.Integer(), nullable=False),
    sa.Column('owner', sa.Text(), nullable=True),
    sa.Column('cycle_number', sa.Integer(), nullable=False),
    sa.Column('start_time', sa.DateTime(), nullable=False),
    sa.Column('end_time', sa.DateTime(), nullable=True),
    sa.Column('collected', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['machine_id'], ['machine.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('load')
    op.drop_table('machine')
    # ### end Alembic commands ###