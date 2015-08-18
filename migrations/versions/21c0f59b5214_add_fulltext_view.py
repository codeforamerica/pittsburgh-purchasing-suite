"""add fulltext view

Revision ID: 21c0f59b5214
Revises: 37b62c1b2866
Create Date: 2015-06-09 14:29:23.154330

"""

# revision identifiers, used by Alembic.
revision = '21c0f59b5214'
down_revision = '37b62c1b2866'

from alembic import op
import sqlalchemy as sa

from purchasing.data.models import TRIGGER_TUPLES

index_set = [
    'tsv_contract_description',
    'tsv_company_name',
    'tsv_detail_value',
    'tsv_line_item_description'
]

def upgrade():
    # grab a connection to the database
    conn = op.get_bind()
    # create the materialized view
    conn.execute(sa.sql.text('''
        CREATE MATERIALIZED VIEW search_view AS (
            SELECT
                c.id::VARCHAR || contract_property.id::VARCHAR || line_item.id::VARCHAR || company.id::VARCHAR AS id,
                c.id AS contract_id,
                company.id AS company_id,
                c.expiration_date, c.financial_id,
                c.description AS contract_description,
                to_tsvector(c.description) AS tsv_contract_description,
                company.company_name AS company_name,
                to_tsvector(company.company_name) AS tsv_company_name,
                contract_property.key AS detail_key,
                contract_property.value AS detail_value,
                to_tsvector(contract_property.value) AS tsv_detail_value,
                line_item.description AS line_item_description,
                to_tsvector(line_item.description) AS tsv_line_item_description
            FROM contract c
            LEFT OUTER JOIN contract_property ON c.id = contract_property.contract_id
            LEFT OUTER JOIN line_item ON c.id = line_item.contract_id
            LEFT OUTER JOIN company_contract_association ON c.id = company_contract_association.contract_id
            LEFT OUTER JOIN company ON company.id = company_contract_association.company_id
        )
    '''))
    # create unique index on ids
    op.create_index(op.f('ix_search_view_id'), 'search_view', ['id'], unique=True)

    # create remaining indices on the tsv columns
    for index in index_set:
        op.create_index(op.f(
            'ix_tsv_{}'.format(index)), 'search_view', [index], postgresql_using='gin'
        )

    # for triggers, we need to build a new function which runs our refresh materialized view
    conn.execute(sa.sql.text('''
        CREATE OR REPLACE FUNCTION trig_refresh_search_view() RETURNS trigger AS
        $$
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY search_view;
            RETURN NULL;
        END;
        $$
        LANGUAGE plpgsql ;
    '''))
    for table, column, _ in TRIGGER_TUPLES:
        conn.execute(sa.sql.text('''
            DROP TRIGGER IF EXISTS tsv_{table}_{column}_trigger ON {table}
        '''.format(table=table, column=column)))
        conn.execute(sa.sql.text('''
            CREATE TRIGGER tsv_{table}_{column}_trigger AFTER TRUNCATE OR INSERT OR DELETE OR UPDATE OF {column}
            ON {table} FOR EACH STATEMENT
            EXECUTE PROCEDURE trig_refresh_search_view()
        '''.format(table=table, column=column)))
    ### end Alembic commands ###


def downgrade():
    # grab a connection to the database
    conn = op.get_bind()
    # drop the materialized view
    conn.execute(sa.sql.text('''
        DROP MATERIALIZED VIEW search_view
    '''))
    for table, column, _ in TRIGGER_TUPLES:
        conn.execute(sa.sql.text('''
            DROP TRIGGER IF EXISTS tsv_{table}_{column}_trigger ON {table}
        '''.format(table=table, column=column)))
    ### end Alembic commands ###
