#!/bin/bash
# Patrol cron scheduler script
# Usage: Add to crontab for regular inspection runs
# Example (every 6 hours):
#   0 */6 * * * /path/to/patrol/scripts/patrol_cron.sh

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DB_PATH="$PROJECT_DIR/patrol.db"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/patrol_cron_$(date +%Y%m%d).log"

echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting scheduled inspection..." >> "$LOG_FILE"

cd "$PROJECT_DIR"

# Get all projects and run inspection for each
python3 -c "
import sqlite3, json, sys
sys.path.insert(0, '.')
from core.engine import InspectionEngine

DB_PATH = '$DB_PATH'
db = sqlite3.connect(DB_PATH)
db.row_factory = sqlite3.Row
projects = db.execute('SELECT id, name FROM projects').fetchall()
db.close()

for p in projects:
    try:
        engine = InspectionEngine(p['id'], DB_PATH)
        record_id = engine.run()
        print(f'Project [{p[\"name\"]}] inspection completed: record_id={record_id}')
    except Exception as e:
        print(f'Project [{p[\"name\"]}] FAILED: {e}')
" >> "$LOG_FILE" 2>&1

echo "$(date '+%Y-%m-%d %H:%M:%S') - Inspection finished" >> "$LOG_FILE"