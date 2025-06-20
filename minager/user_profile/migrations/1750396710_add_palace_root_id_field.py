"""Add palace root id field.

Revision ID: 42c28db61545
Revises: 4c656cdf02ef
Create Date: 2025-06-20 08:18:30.230678

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '42c28db61545'
down_revision: Union[str, None] = '4c656cdf02ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'userprofile',
        sa.Column('palace_root_id', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
    )


def downgrade() -> None:
    op.drop_column('userprofile', 'palace_root_id')
