"""opportunity vendor relationship

Revision ID: 2695fc68b01d
Revises: 501e2f945ff9
Create Date: 2015-07-08 20:30:13.944532

"""

# revision identifiers, used by Alembic.
revision = '2695fc68b01d'
down_revision = '501e2f945ff9'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('opportunity_vendor_association_table',
    sa.Column('opportunity_id', sa.Integer(), nullable=True),
    sa.Column('vendor_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['opportunity_id'], ['opportunity.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['vendor_id'], ['vendor.id'], ondelete='SET NULL')
    )
    op.create_index(op.f('ix_opportunity_vendor_association_table_opportunity_id'), 'opportunity_vendor_association_table', ['opportunity_id'], unique=False)
    op.create_index(op.f('ix_opportunity_vendor_association_table_vendor_id'), 'opportunity_vendor_association_table', ['vendor_id'], unique=False)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_opportunity_vendor_association_table_vendor_id'), table_name='opportunity_vendor_association_table')
    op.drop_index(op.f('ix_opportunity_vendor_association_table_opportunity_id'), table_name='opportunity_vendor_association_table')
    op.drop_table('opportunity_vendor_association_table')
    ### end Alembic commands ###
