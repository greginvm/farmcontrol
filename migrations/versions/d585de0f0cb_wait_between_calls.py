"""Wait between calls

Revision ID: d585de0f0cb
Revises: 1e23308c09f2
Create Date: 2015-03-02 00:03:43.875151

"""

# revision identifiers, used by Alembic.
revision = 'd585de0f0cb'
down_revision = '1e23308c09f2'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('contact', sa.Column('call_wait_minutes', sa.Integer(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('contact', 'call_wait_minutes')
    ### end Alembic commands ###
