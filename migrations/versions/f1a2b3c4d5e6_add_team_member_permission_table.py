"""add team_member_permission table

Revision ID: f1a2b3c4d5e6
Revises: c7f2a1b8e934
Create Date: 2026-09-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'c7f2a1b8e934'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'teammemberpermissionmodel',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('leader_employee_odoo_id', sa.Integer(), nullable=False),
        sa.Column('member_employee_odoo_id', sa.Integer(), nullable=False),
        sa.Column('level', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "level IN ('view', 'validate')",
            name='ck_teammemberpermissionmodel_level',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'leader_employee_odoo_id',
            'member_employee_odoo_id',
            name='uq_teammemberpermission_leader_member',
        ),
    )
    op.create_index(
        op.f('ix_teammemberpermissionmodel_leader_employee_odoo_id'),
        'teammemberpermissionmodel',
        ['leader_employee_odoo_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_teammemberpermissionmodel_member_employee_odoo_id'),
        'teammemberpermissionmodel',
        ['member_employee_odoo_id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_teammemberpermissionmodel_member_employee_odoo_id'),
        table_name='teammemberpermissionmodel',
    )
    op.drop_index(
        op.f('ix_teammemberpermissionmodel_leader_employee_odoo_id'),
        table_name='teammemberpermissionmodel',
    )
    op.drop_table('teammemberpermissionmodel')
