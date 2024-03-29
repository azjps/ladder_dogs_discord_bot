"""Moving settings from hunt to guild

Revision ID: f17dd3158459
Revises: b8b8a390aa12
Create Date: 2023-12-18 22:12:46.072920

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f17dd3158459"
down_revision = "b8b8a390aa12"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("guilds", sa.Column("guild_name", sa.Text(), nullable=True))
    op.add_column("guilds", sa.Column("discussion_channel", sa.Text(), nullable=True))
    op.add_column("guilds", sa.Column("discord_bot_channel", sa.Text(), nullable=True))
    op.add_column("guilds", sa.Column("discord_bot_emoji", sa.Text(), nullable=True))
    op.add_column("guilds", sa.Column("discord_use_voice_channels", sa.BIGINT(), nullable=True))
    op.add_column("guilds", sa.Column("drive_parent_id", sa.Text(), nullable=True))
    op.add_column("guilds", sa.Column("drive_resources_id", sa.Text(), nullable=True))
    op.add_column("guilds", sa.Column("archive_delay", sa.Integer(), nullable=True))
    op.drop_column("hunt_settings", "drive_parent_id")
    op.drop_column("hunt_settings", "discord_use_voice_channels")
    op.drop_column("hunt_settings", "guild_name")
    op.drop_column("hunt_settings", "discord_bot_channel")
    op.drop_column("hunt_settings", "archive_delay")
    op.drop_column("hunt_settings", "discussion_channel")
    op.drop_column("hunt_settings", "drive_resources_id")
    op.drop_column("hunt_settings", "discord_bot_emoji")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "hunt_settings",
        sa.Column("discord_bot_emoji", sa.TEXT(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "hunt_settings",
        sa.Column("drive_resources_id", sa.TEXT(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "hunt_settings",
        sa.Column("discussion_channel", sa.TEXT(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "hunt_settings",
        sa.Column("archive_delay", sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "hunt_settings",
        sa.Column("discord_bot_channel", sa.TEXT(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "hunt_settings", sa.Column("guild_name", sa.TEXT(), autoincrement=False, nullable=True)
    )
    op.add_column(
        "hunt_settings",
        sa.Column("discord_use_voice_channels", sa.BIGINT(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "hunt_settings", sa.Column("drive_parent_id", sa.TEXT(), autoincrement=False, nullable=True)
    )
    op.drop_column("guilds", "archive_delay")
    op.drop_column("guilds", "drive_resources_id")
    op.drop_column("guilds", "drive_parent_id")
    op.drop_column("guilds", "discord_use_voice_channels")
    op.drop_column("guilds", "discord_bot_emoji")
    op.drop_column("guilds", "discord_bot_channel")
    op.drop_column("guilds", "discussion_channel")
    op.drop_column("guilds", "guild_name")
    # ### end Alembic commands ###
