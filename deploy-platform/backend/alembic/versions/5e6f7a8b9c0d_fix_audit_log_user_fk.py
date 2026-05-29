"""fix audit_log user_id FK to SET NULL on delete

Revision ID: 5e6f7a8b9c0d
Revises: 29aa758b05d7
Create Date: 2026-05-29

"""
from typing import Sequence, Union

from alembic import op


revision: str = "5e6f7a8b9c0d"
down_revision: Union[str, None] = "4a2b1c3d5e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE audit_logs_new (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action VARCHAR(50) NOT NULL,
            target_type VARCHAR(50),
            target_id INTEGER,
            detail TEXT,
            ip_address VARCHAR(50),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    """)
    op.execute("INSERT INTO audit_logs_new SELECT * FROM audit_logs")
    op.execute("DROP TABLE audit_logs")
    op.execute("ALTER TABLE audit_logs_new RENAME TO audit_logs")


def downgrade() -> None:
    op.execute("""
        CREATE TABLE audit_logs_new (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action VARCHAR(50) NOT NULL,
            target_type VARCHAR(50),
            target_id INTEGER,
            detail TEXT,
            ip_address VARCHAR(50),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    op.execute("INSERT INTO audit_logs_new SELECT * FROM audit_logs")
    op.execute("DROP TABLE audit_logs")
    op.execute("ALTER TABLE audit_logs_new RENAME TO audit_logs")
