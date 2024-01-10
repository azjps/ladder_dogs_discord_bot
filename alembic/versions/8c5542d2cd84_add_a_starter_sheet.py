"""Add a starter sheet

Revision ID: 8c5542d2cd84
Revises: ea4259733a37
Create Date: 2023-12-26 19:53:42.049429

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8c5542d2cd84"
down_revision = "ea4259733a37"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("guilds", sa.Column("drive_starter_sheet_id", sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("guilds", "drive_starter_sheet_id")
    # ### end Alembic commands ###
