"""migrate_chat_history_to_alembic_with_audio_url

Revision ID: 75796d073cb2
Revises: 31a4fbff90e7
Create Date: 2025-09-09 02:47:19.386052+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
# 修订标识符，由 Alembic 使用。
revision: str = '75796d073cb2'
down_revision: Union[str, None] = '31a4fbff90e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
#检查表是否存在并进行相应处理
    connection = op.get_bind()
#检查chat_history表是否存在
    table_exists = connection.execute(
        sa.text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'chat_history')")
    ).scalar()
    
    if table_exists:
# 表存在（由langchain_postgres创建），添加audio_url列
        op.add_column('chat_history', sa.Column('audio_url', sa.String(), nullable=True))
#创建索引前检查索引是否存在
        index_exists = connection.execute(
            sa.text("""
            SELECT EXISTS (
                SELECT FROM pg_indexes 
                WHERE tablename = 'chat_history' AND indexname = 'idx_chat_history_session_id'
            )
            """)
        ).scalar()
        
        if not index_exists:
            op.create_index('idx_chat_history_session_id', 'chat_history', ['session_id'])
    else:
# 表不存在，使用包括audio_url 的所有列创建它
        op.create_table('chat_history',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('message', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column('audio_url', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_chat_history_session_id', 'chat_history', ['session_id'])


def downgrade() -> None:
# 只删除audio_url列，不要删除整个表
# 因为它可能是由 langchain_postgres 创建的
    connection = op.get_bind()
#检查audio_url列是否存在
    column_exists = connection.execute(
        sa.text("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_name = 'chat_history' AND column_name = 'audio_url'
        )
        """)
    ).scalar()
    
    if column_exists:
        op.drop_column('chat_history', 'audio_url')
