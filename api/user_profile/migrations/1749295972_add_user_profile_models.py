"""Add user profile models.

Revision ID: 4c656cdf02ef
Revises:
Create Date: 2025-06-07 14:32:52.445118
"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = '4c656cdf02ef'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = ('user_profile',)
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'userprofile',
        sa.Column('user_id', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=250), nullable=False),
        sa.Column('bio', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=False),
        sa.Column('experience', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('user_id'),
    )


def downgrade() -> None:
    op.drop_table('userprofile')
