"""Scheduler management"""
import json
import sqlite3
from datetime import datetime


class SchedulerManager:
    """定时调度管理"""

    def __init__(self, db_path):
        self.db_path = db_path

    def _get_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_enabled_schedules(self):
        """Get all enabled schedules"""
        db = self._get_db()
        schedules = db.execute("""
            SELECT s.*, p.name as project_name, p.prometheus_url
            FROM schedules s
            JOIN projects p ON s.project_id = p.id
            WHERE s.enabled = 1
        """).fetchall()
        db.close()
        return [dict(s) for s in schedules]

    def run_due_tasks(self, engine_factory):
        """Execute all due scheduled inspections"""
        schedules = self.get_enabled_schedules()
        results = []
        for sched in schedules:
            try:
                engine = engine_factory(sched["project_id"])
                record_id = engine.run()
                results.append({
                    "project_id": sched["project_id"],
                    "project_name": sched["project_name"],
                    "record_id": record_id,
                    "status": "success"
                })
            except Exception as e:
                results.append({
                    "project_id": sched["project_id"],
                    "project_name": sched["project_name"],
                    "status": "failed",
                    "error": str(e)
                })
        return results