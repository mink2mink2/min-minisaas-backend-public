"""Populate nicknames for existing users without nicknames

Revision ID: 20260304_0009
Revises: 20260304_0008
Create Date: 2026-03-04 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import random
import string


def generate_random_nickname() -> str:
    """임의의 닉네임 생성"""
    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    return f"User_{random_str}"


# revision identifiers, used by Alembic.
revision = "20260304_0009"
down_revision = "20260304_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 닉네임이 없는 사용자들을 찾아서 자동으로 생성된 닉네임 할당
    connection = op.get_bind()

    # nickname이 NULL인 사용자 조회
    users_without_nickname = connection.execute(
        sa.text("SELECT id FROM users WHERE nickname IS NULL ORDER BY created_at")
    ).fetchall()

    # 각 사용자에게 고유한 닉네임 할당
    for user_row in users_without_nickname:
        user_id = user_row[0]
        nickname = generate_random_nickname()

        # 중복 확인 (매우 드물지만 가능성이 있으므로)
        max_attempts = 10
        attempts = 0
        while attempts < max_attempts:
            existing = connection.execute(
                sa.text("SELECT COUNT(*) FROM users WHERE nickname = :nickname"),
                {"nickname": nickname}
            ).scalar()

            if existing == 0:
                break

            nickname = generate_random_nickname()
            attempts += 1

        # 닉네임 업데이트
        connection.execute(
            sa.text("UPDATE users SET nickname = :nickname WHERE id = :user_id"),
            {"nickname": nickname, "user_id": str(user_id)}
        )

    connection.commit()


def downgrade() -> None:
    # 롤백 시 자동 생성된 닉네임만 삭제 (User_로 시작하는 것들)
    connection = op.get_bind()
    connection.execute(
        sa.text("UPDATE users SET nickname = NULL WHERE nickname LIKE 'User_%'")
    )
    connection.commit()
