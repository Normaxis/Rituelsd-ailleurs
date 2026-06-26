"""planning notes and cabin compatibility

Revision ID: 0001_planning_notes
Revises: 
Create Date: 2026-06-26
"""
from alembic import op
import sqlalchemy as sa


revision = '0001_planning_notes'
down_revision = None
branch_labels = None
depends_on = None


def _table_names(bind):
    return set(sa.inspect(bind).get_table_names())


def _column_names(bind, table_name):
    if table_name not in _table_names(bind):
        return set()
    return {column['name'] for column in sa.inspect(bind).get_columns(table_name)}


def _constraint_names(bind, table_name):
    if table_name not in _table_names(bind):
        return set()
    inspector = sa.inspect(bind)
    names = set()
    for constraint in inspector.get_unique_constraints(table_name):
        if constraint.get('name'):
            names.add(constraint['name'])
    return names


def upgrade():
    bind = op.get_bind()
    tables = _table_names(bind)

    if 'appointment' in tables and 'note' not in _column_names(bind, 'appointment'):
        with op.batch_alter_table('appointment') as batch_op:
            batch_op.add_column(sa.Column('note', sa.Text(), nullable=True, server_default=''))

    if 'treatment_cabin_compatibility' not in tables:
        op.create_table(
            'treatment_cabin_compatibility',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('treatment_id', sa.Integer(), nullable=False),
            sa.Column('cabin_id', sa.Integer(), nullable=False),
            sa.Column('is_allowed', sa.Boolean(), nullable=False, server_default=sa.text('1')),
            sa.Column('note', sa.String(length=255), nullable=True, server_default=''),
            sa.ForeignKeyConstraint(['cabin_id'], ['cabin.id']),
            sa.ForeignKeyConstraint(['treatment_id'], ['treatment.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('treatment_id', 'cabin_id', name='uniq_treatment_cabin_compatibility'),
        )


def downgrade():
    bind = op.get_bind()
    tables = _table_names(bind)

    if 'treatment_cabin_compatibility' in tables:
        op.drop_table('treatment_cabin_compatibility')

    if 'appointment' in tables and 'note' in _column_names(bind, 'appointment'):
        with op.batch_alter_table('appointment') as batch_op:
            batch_op.drop_column('note')
