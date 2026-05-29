"""add timeout_seconds to upgrade_tasks

Revision ID: 4a2b1c3d5e6f
Revises: 29aa758b05d7
Create Date: 2026-05-28 11:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '4a2b1c3d5e6f'
down_revision: Union[str, None] = '29aa758b05d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('upgrade_tasks', sa.Column('timeout_seconds', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('upgrade_tasks', 'timeout_seconds')
