"""Add auth user model.

Revision ID: aeeb29d9256e
Revises:
Create Date: 2025-06-11 15:01:07.914908

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'aeeb29d9256e'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = ('auth',)
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'auth.users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('password', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('auth.users')
