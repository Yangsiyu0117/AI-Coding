"""fix upgrade_tasks created_by FK to SET NULL on delete

Revision ID: 6f7a8b9c0d1e
Revises: 5e6f7a8b9c0d
Create Date: 2026-05-29

"""
from typing import Sequence, Union

from alembic import op


revision: str = "6f7a8b9c0d1e"
down_revision: Union[str, None] = "5e6f7a8b9c0d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE upgrade_tasks_new (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            environment_id INTEGER NOT NULL,
            title VARCHAR(200) NOT NULL,
            status VARCHAR(30),
            failure_strategy VARCHAR(20),
            rollback_status VARCHAR(20),
            is_rollback BOOLEAN,
            timeout_seconds INTEGER,
            created_by INTEGER,
            started_at DATETIME,
            finished_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY(environment_id) REFERENCES environments(id)
        )
    """)
    op.execute("INSERT INTO upgrade_tasks_new SELECT * FROM upgrade_tasks")
    op.execute("DROP TABLE upgrade_tasks")
    op.execute("ALTER TABLE upgrade_tasks_new RENAME TO upgrade_tasks")


def downgrade() -> None:
    op.execute("""
        CREATE TABLE upgrade_tasks_new (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            environment_id INTEGER NOT NULL,
            title VARCHAR(200) NOT NULL,
            status VARCHAR(30),
            failure_strategy VARCHAR(20),
            rollback_status VARCHAR(20),
            is_rollback BOOLEAN,
            timeout_seconds INTEGER,
            created_by INTEGER,
            started_at DATETIME,
            finished_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(created_by) REFERENCES users(id),
            FOREIGN KEY(environment_id) REFERENCES environments(id)
        )
    """)
    op.execute("INSERT INTO upgrade_tasks_new SELECT * FROM upgrade_tasks")
    op.execute("DROP TABLE upgrade_tasks")
    op.execute("ALTER TABLE upgrade_tasks_new RENAME TO upgrade_tasks")
