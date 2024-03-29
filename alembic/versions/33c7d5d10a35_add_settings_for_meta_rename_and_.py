"""Add settings for meta rename and archive delay

Revision ID: 33c7d5d10a35
Revises: ff7c50e73243
Create Date: 2023-12-14 19:03:15.211462

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "33c7d5d10a35"
down_revision = "ff7c50e73243"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("hunt_settings", sa.Column("discussion_channel", sa.Text(), nullable=True))
    op.add_column("hunt_settings", sa.Column("archive_delay", sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("hunt_settings", "archive_delay")
    op.drop_column("hunt_settings", "discussion_channel")
    # ### end Alembic commands ###
