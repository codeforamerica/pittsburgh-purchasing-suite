"""job_status_table

Revision ID: 409abb6abb99
Revises: 3f80f0c8adf1
Create Date: 2015-09-01 17:05:02.609696

"""

# revision identifiers, used by Alembic.
revision = '409abb6abb99'
down_revision = '3f80f0c8adf1'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('job_status',
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('date', sa.DateTime(), nullable=False),
    sa.Column('status', sa.String(), nullable=True),
    sa.Column('info', sa.Text(), nullable=True),
    sa.Column('updated_by_id', sa.Integer(), nullable=True),
    sa.Column('created_by_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name='created_by_id_fkey', use_alter=True),
    sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], name='updated_by_id_fkey', use_alter=True),
    sa.PrimaryKeyConstraint('name', 'date')
    )

    op.alter_column('opportunity', 'planned_advertise', new_column_name='planned_publish')
    op.alter_column('opportunity', 'planned_open', new_column_name='planned_submission_start')
    op.alter_column('opportunity', 'planned_deadline', new_column_name='planned_submission_end')

    op.add_column('opportunity', sa.Column('publish_notification_sent', sa.Boolean(), nullable=False, server_default=sa.schema.DefaultClause('false')))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###

    op.alter_column('opportunity', 'planned_publish', new_column_name='planned_advertise')
    op.alter_column('opportunity', 'planned_submission_start', new_column_name='planned_open')
    op.alter_column('opportunity', 'planned_submission_end', new_column_name='planned_deadline')

    op.drop_table('job_status')

    op.drop_column('opportunity', 'publish_notification_sent')
    ### end Alembic commands ###
