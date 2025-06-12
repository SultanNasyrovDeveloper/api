"""Add auth user model.

Revision ID: c05e79534128
Revises:
Create Date: 2025-06-12 13:56:57.973111

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = 'c05e79534128'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = ('auth',)
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'auth.users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('password', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('is_email_verified', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )


def downgrade() -> None:
    op.drop_table('auth.users')
