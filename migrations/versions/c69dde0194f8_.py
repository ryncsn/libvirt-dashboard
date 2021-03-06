"""Add support for tags and properties.

Revision ID: c69dde0194f8
Revises: d970ebbc5efa
Create Date: 2016-09-26 15:26:28.263507

"""

# revision identifiers, used by Alembic.
revision = 'c69dde0194f8'
down_revision = 'd970ebbc5efa'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('tag',
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('desc', sa.String(length=255), nullable=True),
    sa.PrimaryKeyConstraint('name')
    )
    op.create_table('property',
    sa.Column('run_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('value', sa.String(length=1024), nullable=False),
    sa.ForeignKeyConstraint(['run_id'], ['run.id'], ),
    sa.PrimaryKeyConstraint('run_id', 'name')
    )
    op.create_table('test_run_tags',
    sa.Column('run_id', sa.Integer(), nullable=True),
    sa.Column('tag_name', sa.String(length=255), nullable=True),
    sa.ForeignKeyConstraint(['run_id'], ['run.id'], ),
    sa.ForeignKeyConstraint(['tag_name'], ['tag.name'], )
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('test_run_tags')
    op.drop_table('property')
    op.drop_table('tag')
    ### end Alembic commands ###
