"""empty message

Revision ID: f6d833096f97
Revises: 79d03eea0366
Create Date: 2016-11-09 13:53:09.406395

"""

# revision identifiers, used by Alembic.
revision = 'f6d833096f97'
down_revision = '79d03eea0366'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('linkage_results',
    sa.Column('run_id', sa.Integer(), nullable=False),
    sa.Column('manual_result_id', sa.String(length=255), nullable=False),
    sa.Column('auto_result_id', sa.String(length=65535), nullable=False),
    sa.Column('error', sa.String(length=255), nullable=True),
    sa.Column('result', sa.String(length=255), nullable=True),
    sa.ForeignKeyConstraint(['run_id', 'auto_result_id'], [u'auto_result.run_id', u'auto_result.case'], ),
    sa.ForeignKeyConstraint(['run_id', 'manual_result_id'], [u'manual_result.run_id', u'manual_result.case'], ),
    sa.ForeignKeyConstraint(['run_id'], ['run.id'], ),
    sa.PrimaryKeyConstraint('run_id', 'manual_result_id', 'auto_result_id')
    )
    op.drop_column('auto_result', 'linkage_result')
    op.drop_column('auto_result', 'error')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('auto_result', sa.Column('error', sa.VARCHAR(length=255), nullable=True))
    op.add_column('auto_result', sa.Column('linkage_result', sa.VARCHAR(length=255), nullable=True))
    op.drop_table('linkage_results')
    ### end Alembic commands ###
