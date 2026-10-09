"""add validity dates to team member permission

Revision ID: d4e5f6a7b8c9
Revises: f1a2b3c4d5e6
Create Date: 2026-10-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Ambas columnas son NULL-ables: los permisos que ya existen quedan sin
    vencimiento, igual que hasta ahora.
    """
    op.add_column(
        'teammemberpermissionmodel', sa.Column('valid_from', sa.Date(), nullable=True)
    )
    op.add_column(
        'teammemberpermissionmodel', sa.Column('valid_until', sa.Date(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('teammemberpermissionmodel', 'valid_until')
    op.drop_column('teammemberpermissionmodel', 'valid_from')
