"""Blog domain tables

Revision ID: 20260216_0005
Revises: 20260215_0004
Create Date: 2026-02-16 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260216_0005'
down_revision = '20260215_0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create blog_categories table
    op.create_table(
        'blog_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_blog_categories_name', 'blog_categories', ['name'], unique=False)

    # Create blog_posts table
    op.create_table(
        'blog_posts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('slug', sa.String(200), nullable=False, unique=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('excerpt', sa.String(500), nullable=True),
        sa.Column('featured_image_url', sa.String(500), nullable=True),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('is_published', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('like_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('comment_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['category_id'], ['blog_categories.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_blog_posts_author_id', 'blog_posts', ['author_id'], unique=False)
    op.create_index('ix_blog_posts_published_at', 'blog_posts', ['published_at'], unique=False)
    op.create_index('ix_blog_posts_like_count', 'blog_posts', ['like_count'], unique=False)

    # Create blog_likes table
    op.create_table(
        'blog_likes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('post_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['post_id'], ['blog_posts.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('post_id', 'user_id', name='uq_blog_likes_post_user'),
    )
    op.create_index('ix_blog_likes_post_id', 'blog_likes', ['post_id'], unique=False)
    op.create_index('ix_blog_likes_user_id', 'blog_likes', ['user_id'], unique=False)

    # Create blog_subscriptions table (Follow)
    op.create_table(
        'blog_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subscriber_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['subscriber_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('subscriber_id', 'author_id', name='uq_blog_subscriptions_subscriber_author'),
    )
    op.create_index('ix_blog_subscriptions_subscriber_id', 'blog_subscriptions', ['subscriber_id'], unique=False)
    op.create_index('ix_blog_subscriptions_author_id', 'blog_subscriptions', ['author_id'], unique=False)


def downgrade() -> None:
    op.drop_table('blog_subscriptions')
    op.drop_table('blog_likes')
    op.drop_table('blog_posts')
    op.drop_table('blog_categories')
