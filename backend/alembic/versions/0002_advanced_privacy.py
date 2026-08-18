"""Add advanced audiences, profile privacy and followers.

Revision ID: 0002_advanced_privacy
Revises: 0001_socialn_baseline
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_advanced_privacy"
down_revision = "0001_socialn_baseline"
branch_labels = None
depends_on = None

AUDIENCES = "'public','friends','friends_except','specific_friends','followers','custom','only_me'"


def upgrade() -> None:
    op.add_column("users", sa.Column("privacy_settings", sa.Text(), nullable=True))
    op.add_column("posts", sa.Column("audience_config", sa.Text(), nullable=True))
    op.add_column("albums", sa.Column("audience_config", sa.Text(), nullable=True))
    op.execute(f"ALTER TABLE posts MODIFY privacy ENUM({AUDIENCES}) NOT NULL DEFAULT 'public'")
    op.execute(f"ALTER TABLE albums MODIFY privacy ENUM({AUDIENCES}) NOT NULL DEFAULT 'friends'")
    op.execute(f"ALTER TABLE album_media MODIFY privacy ENUM({AUDIENCES}) NOT NULL DEFAULT 'friends'")
    op.create_table(
        "follows",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("follower_id", sa.Integer(), nullable=False),
        sa.Column("followed_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["follower_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["followed_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("follower_id", "followed_id", name="uq_follow_pair"),
    )
    op.create_index("ix_follows_follower_id", "follows", ["follower_id"])
    op.create_index("ix_follows_followed_id", "follows", ["followed_id"])


def downgrade() -> None:
    op.drop_table("follows")
    op.drop_column("albums", "audience_config")
    op.drop_column("posts", "audience_config")
    op.drop_column("users", "privacy_settings")
