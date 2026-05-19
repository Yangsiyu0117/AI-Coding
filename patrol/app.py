#!/usr/bin/env python3
"""Patrol Inspection System - Flask Backend"""
import json
import os
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory

from core.engine import InspectionEngine
from core.prometheus_client import PrometheusClient

app = Flask(__name__, static_folder="web/dist", static_url_path="")
# Server external URL for notification links (overrides request.host_url)
SERVER_BASE_URL = os.environ.get("PATROL_BASE_URL", "").rstrip("/")
if SERVER_BASE_URL:
    SERVER_BASE_URL += "/"

DB_PATH = os.environ.get("PATROL_DB_PATH", "patrol.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    env TEXT DEFAULT 'production',
    description TEXT,
    prometheus_url TEXT NOT NULL,
    auth_enabled INTEGER DEFAULT 0,
    auth_username TEXT,
    auth_password TEXT,
    headers_json TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS plugin_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    plugin_name TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    job_pattern TEXT NOT NULL,
    thresholds_json TEXT DEFAULT '{}',
    extra_config_json TEXT DEFAULT '{}',
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS notification_channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    channel_type TEXT NOT NULL,
    config_json TEXT NOT NULL,
    report_format TEXT DEFAULT 'markdown',
    enabled INTEGER DEFAULT 1,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS global_thresholds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    metric_key TEXT NOT NULL,
    threshold_value REAL NOT NULL,
    severity TEXT DEFAULT 'critical',
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS inspection_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    trigger_type TEXT DEFAULT 'scheduled',
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    status TEXT DEFAULT 'running',
    summary_json TEXT,
    report_markdown TEXT,
    report_html TEXT,
    total_items INTEGER DEFAULT 0,
    abnormal_items INTEGER DEFAULT 0,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS inspection_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id INTEGER NOT NULL,
    plugin_name TEXT,
    target_instance TEXT,
    metric_name TEXT,
    current_value TEXT,
    threshold_value TEXT,
    status TEXT,
    detail TEXT,
    FOREIGN KEY (record_id) REFERENCES inspection_records(id)
);

CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    cron_expression TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    description TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS datasource_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    ds_type TEXT DEFAULT 'prometheus',
    url TEXT NOT NULL,
    auth_enabled INTEGER DEFAULT 0,
    auth_username TEXT,
    auth_password TEXT,
    headers_json TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS notification_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id INTEGER,
    channel_id INTEGER,
    channel_type TEXT NOT NULL,
    project_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (record_id) REFERENCES inspection_records(id)
);
"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db():
    db = get_db()
    db.executescript(SCHEMA)
    # Migration: add columns to plugin_configs (if not exist)
    try:
        db.execute("ALTER TABLE plugin_configs ADD COLUMN datasource_id INTEGER DEFAULT NULL")
    except (sqlite3.OperationalError, sqlite3.Error):
        pass  # Column already exists
    try:
        db.execute("ALTER TABLE plugin_configs ADD COLUMN filter_config_json TEXT DEFAULT '{}'")
    except (sqlite3.OperationalError, sqlite3.Error):
        pass  # Column already exists
    # Insert default settings if not exist
    defaults = [
        ("records_retention_days", "90"),
        ("details_retention_days", "90"),
    ]
    for key, val in defaults:
        db.execute(
            "INSERT OR IGNORE INTO app_settings (key, value) VALUES (?, ?)",
            (key, val)
        )
    db.commit()
    db.close()


# ==================== 项目管理 ====================

@app.route("/api/projects", methods=["GET"])
def list_projects():
    db = get_db()
    projects = db.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
    return jsonify([dict(p) for p in projects])


@app.route("/api/projects/<int:project_id>", methods=["GET"])
def get_project(project_id):
    db = get_db()
    project = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if not project:
        return jsonify({"error": "项目不存在"}), 404
    return jsonify(dict(project))


@app.route("/api/projects", methods=["POST"])
def create_project():
    data = request.json
    db = get_db()
    cursor = db.execute("""
        INSERT INTO projects (name, env, description, prometheus_url,
                             auth_enabled, auth_username, auth_password, headers_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (data["name"], data.get("env", "production"), data.get("description", ""),
          data["prometheus_url"], int(data.get("auth_enabled", 0)),
          data.get("auth_username", ""), data.get("auth_password", ""),
          json.dumps(data.get("headers", {}))))
    db.commit()
    return jsonify({"id": cursor.lastrowid, "message": "创建成功"})


@app.route("/api/projects/<int:project_id>", methods=["PUT"])
def update_project(project_id):
    data = request.json
    db = get_db()
    db.execute("""
        UPDATE projects SET name=?, env=?, description=?, prometheus_url=?,
               auth_enabled=?, auth_username=?, auth_password=?, headers_json=?,
               updated_at=CURRENT_TIMESTAMP
        WHERE id=?
    """, (data["name"], data.get("env"), data.get("description"),
          data["prometheus_url"], int(data.get("auth_enabled", 0)),
          data.get("auth_username", ""), data.get("auth_password", ""),
          json.dumps(data.get("headers", {})), project_id))
    db.commit()
    return jsonify({"message": "更新成功"})


@app.route("/api/projects/<int:project_id>", methods=["DELETE"])
def delete_project(project_id):
    db = get_db()
    db.execute("DELETE FROM projects WHERE id=?", (project_id,))
    db.execute("DELETE FROM plugin_configs WHERE project_id=?", (project_id,))
    db.execute("DELETE FROM notification_channels WHERE project_id=?", (project_id,))
    db.execute("DELETE FROM global_thresholds WHERE project_id=?", (project_id,))
    db.execute("DELETE FROM inspection_records WHERE project_id=?", (project_id,))
    db.execute("DELETE FROM schedules WHERE project_id=?", (project_id,))
    db.commit()
    return jsonify({"message": "删除成功"})


# ==================== 插件配置 ====================

@app.route("/api/projects/<int:project_id>/plugins", methods=["GET"])
def list_plugin_configs(project_id):
    db = get_db()
    configs = db.execute(
        "SELECT * FROM plugin_configs WHERE project_id=?", (project_id,)
    ).fetchall()
    return jsonify([dict(c) for c in configs])


@app.route("/api/projects/<int:project_id>/plugins", methods=["POST"])
def save_plugin_config(project_id):
    data = request.json
    db = get_db()
    db.execute("DELETE FROM plugin_configs WHERE project_id=?", (project_id,))
    for plugin in data.get("plugins", []):
        db.execute("""
            INSERT INTO plugin_configs (project_id, plugin_name, enabled,
                                       job_pattern, thresholds_json, extra_config_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (project_id, plugin["plugin_name"], int(plugin.get("enabled", 1)),
              plugin["job_pattern"], json.dumps(plugin.get("thresholds", {})),
              json.dumps(plugin.get("extra_config", {}))))
    db.commit()
    return jsonify({"message": "保存成功"})


# ==================== 通知渠道 ====================

@app.route("/api/projects/<int:project_id>/channels", methods=["GET"])
def list_channels(project_id):
    db = get_db()
    channels = db.execute(
        "SELECT * FROM notification_channels WHERE project_id=?", (project_id,)
    ).fetchall()
    result = []
    for c in channels:
        d = dict(c)
        d["config"] = json.loads(d.pop("config_json", "{}"))
        result.append(d)
    return jsonify(result)


@app.route("/api/projects/<int:project_id>/channels", methods=["POST"])
def save_channel(project_id):
    data = request.json
    db = get_db()
    cursor = db.execute("""
        INSERT INTO notification_channels (project_id, channel_type, config_json,
                                          report_format, enabled)
        VALUES (?, ?, ?, ?, ?)
    """, (project_id, data["channel_type"], json.dumps(data["config"]),
          data.get("report_format", "markdown"), int(data.get("enabled", 1))))
    db.commit()
    return jsonify({"id": cursor.lastrowid, "message": "保存成功"})


@app.route("/api/projects/<int:project_id>/channels/<int:channel_id>", methods=["DELETE"])
def delete_channel(project_id, channel_id):
    db = get_db()
    db.execute("DELETE FROM notification_channels WHERE id=? AND project_id=?",
               (channel_id, project_id))
    db.commit()
    return jsonify({"message": "删除成功"})


@app.route("/api/projects/<int:project_id>/channels/<int:channel_id>", methods=["PUT"])
def update_channel(project_id, channel_id):
    data = request.json
    db = get_db()
    db.execute("""
        UPDATE notification_channels SET channel_type=?, config_json=?,
               report_format=?, enabled=?
        WHERE id=? AND project_id=?
    """, (data["channel_type"], json.dumps(data["config"]),
          data.get("report_format", "markdown"), int(data.get("enabled", 1)),
          channel_id, project_id))
    db.commit()
    return jsonify({"message": "更新成功"})


# ==================== 全局阈值 ====================

@app.route("/api/projects/<int:project_id>/thresholds", methods=["GET"])
def list_thresholds(project_id):
    db = get_db()
    thresholds = db.execute(
        "SELECT * FROM global_thresholds WHERE project_id=?", (project_id,)
    ).fetchall()
    return jsonify([dict(t) for t in thresholds])


@app.route("/api/projects/<int:project_id>/thresholds", methods=["POST"])
def save_threshold(project_id):
    data = request.json
    db = get_db()
    cursor = db.execute("""
        INSERT INTO global_thresholds (project_id, metric_key, threshold_value, severity)
        VALUES (?, ?, ?, ?)
    """, (project_id, data["metric_key"], data["threshold_value"], data.get("severity", "critical")))
    db.commit()
    return jsonify({"id": cursor.lastrowid, "message": "保存成功"})


@app.route("/api/projects/<int:project_id>/thresholds/<int:threshold_id>", methods=["DELETE"])
def delete_threshold(project_id, threshold_id):
    db = get_db()
    db.execute("DELETE FROM global_thresholds WHERE id=? AND project_id=?",
               (threshold_id, project_id))
    db.commit()
    return jsonify({"message": "删除成功"})


# ==================== 调度配置 ====================

@app.route("/api/projects/<int:project_id>/schedules", methods=["GET"])
def list_schedules(project_id):
    db = get_db()
    schedules = db.execute(
        "SELECT * FROM schedules WHERE project_id=?", (project_id,)
    ).fetchall()
    return jsonify([dict(s) for s in schedules])


@app.route("/api/projects/<int:project_id>/schedules", methods=["POST"])
def save_schedule(project_id):
    data = request.json
    db = get_db()
    if data.get("id"):
        print(f"DEBUG UPDATE: id={data['id']}, cron={data.get('cron_expression')}", flush=True)
        db.execute("""
            UPDATE schedules SET cron_expression=?, enabled=?, description=?
            WHERE id=? AND project_id=?
        """, (data["cron_expression"], int(data.get("enabled", 1)),
              data.get("description", ""), data["id"], project_id))
    else:
        print(f"DEBUG INSERT: cron={data.get('cron_expression')}", flush=True)
        db.execute("""
            INSERT INTO schedules (project_id, cron_expression, enabled, description)
            VALUES (?, ?, ?, ?)
        """, (project_id, data["cron_expression"], int(data.get("enabled", 1)),
              data.get("description", "")))
    db.commit()
    _reload_scheduled_jobs()
    return jsonify({"message": "保存成功"})


@app.route("/api/projects/<int:project_id>/schedules/<int:schedule_id>", methods=["DELETE"])
def delete_schedule(project_id, schedule_id):
    db = get_db()
    db.execute("DELETE FROM schedules WHERE id=? AND project_id=?",
               (schedule_id, project_id))
    db.commit()
    _reload_scheduled_jobs()
    return jsonify({"message": "删除成功"})


@app.route("/api/projects/<int:project_id>/schedules/<int:schedule_id>", methods=["PUT"])
def update_schedule(project_id, schedule_id):
    data = request.json
    db = get_db()
    db.execute("""
        UPDATE schedules SET cron_expression=?, enabled=?, description=?
        WHERE id=? AND project_id=?
    """, (data.get("cron_expression", "0 9 * * *"), int(data.get("enabled", 1)),
          data.get("description", ""), schedule_id, project_id))
    db.commit()
    _reload_scheduled_jobs()
    return jsonify({"message": "更新成功"})


# ==================== 数据源管理 ====================


@app.route("/api/projects/<int:project_id>/datasources", methods=["GET"])
def list_datasources(project_id):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM datasource_configs WHERE project_id=? ORDER BY created_at DESC",
        (project_id,)
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/projects/<int:project_id>/datasources", methods=["POST"])
def create_datasource(project_id):
    data = request.json
    db = get_db()
    cursor = db.execute("""
        INSERT INTO datasource_configs
            (project_id, name, ds_type, url, auth_enabled, auth_username, auth_password, headers_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (project_id, data["name"], data.get("ds_type", "prometheus"),
          data["url"], int(data.get("auth_enabled", 0)),
          data.get("auth_username", ""), data.get("auth_password", ""),
          json.dumps(data.get("headers", {}))))
    db.commit()
    return jsonify({"id": cursor.lastrowid, "message": "创建成功"})


@app.route("/api/projects/<int:project_id>/datasources/<int:ds_id>", methods=["PUT"])
def update_datasource(project_id, ds_id):
    data = request.json
    db = get_db()
    db.execute("""
        UPDATE datasource_configs SET
            name=?, ds_type=?, url=?, auth_enabled=?, auth_username=?, auth_password=?,
            headers_json=?, created_at=CURRENT_TIMESTAMP
        WHERE id=? AND project_id=?
    """, (data["name"], data.get("ds_type", "prometheus"),
          data["url"], int(data.get("auth_enabled", 0)),
          data.get("auth_username", ""), data.get("auth_password", ""),
          json.dumps(data.get("headers", {})), ds_id, project_id))
    db.commit()
    return jsonify({"message": "更新成功"})


@app.route("/api/projects/<int:project_id>/datasources/<int:ds_id>", methods=["DELETE"])
def delete_datasource(project_id, ds_id):
    db = get_db()
    # Reset plugin_configs referencing this datasource
    db.execute("UPDATE plugin_configs SET datasource_id=NULL WHERE datasource_id=? AND project_id=?",
               (ds_id, project_id))
    db.execute("DELETE FROM datasource_configs WHERE id=? AND project_id=?",
               (ds_id, project_id))
    db.commit()
    return jsonify({"message": "删除成功"})


@app.route("/api/projects/<int:project_id>/datasources/<int:ds_id>/test", methods=["POST"])
def test_datasource(project_id, ds_id):
    db = get_db()
    row = db.execute(
        "SELECT * FROM datasource_configs WHERE id=? AND project_id=?",
        (ds_id, project_id)
    ).fetchone()
    if not row:
        return jsonify({"error": "数据源不存在"}), 404

    try:
        from core.datasource import DataSourceConfig, get_default_registry
        cfg = DataSourceConfig(
            ds_type=row["ds_type"],
            url=row["url"],
            auth_enabled=bool(row["auth_enabled"]),
            username=row["auth_username"] or "",
            password=row["auth_password"] or "",
            headers=json.loads(row["headers_json"] or "{}")
        )
        registry = get_default_registry()
        ds = registry.create(cfg)
        ok, msg = ds.test_connection()
        return jsonify({"status": "success" if ok else "failed", "message": msg})
    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)}), 500


# ==================== Target自动发现 ====================

@app.route("/api/projects/<int:project_id>/discover", methods=["GET"])
def discover_targets(project_id):
    db = get_db()
    project = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if not project:
        return jsonify({"error": "项目不存在"}), 404

    prom = PrometheusClient(
        url=project["prometheus_url"],
        auth_enabled=bool(project["auth_enabled"]),
        username=project["auth_username"] or "",
        password=project["auth_password"] or ""
    )
    try:
        targets = prom.get_targets()
        job_summary = {}
        for t in targets.get("activeTargets", []):
            job = t.get("labels", {}).get("job", "unknown")
            if job not in job_summary:
                job_summary[job] = {"total": 0, "up": 0, "down": 0, "instances": []}
            job_summary[job]["total"] += 1
            if t.get("health") == "up":
                job_summary[job]["up"] += 1
            else:
                job_summary[job]["down"] += 1
            job_summary[job]["instances"].append(t.get("labels", {}).get("instance", ""))
        return jsonify({"jobs": job_summary})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== 巡检执行与记录 ====================

@app.route("/api/projects/<int:project_id>/inspect", methods=["POST"])
def trigger_inspection(project_id):
    engine = InspectionEngine(project_id, DB_PATH)
    try:
        record_id = engine.run()
        return jsonify({"record_id": record_id, "message": "巡检已触发"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/projects/<int:project_id>/records", methods=["GET"])
def list_records(project_id):
    db = get_db()
    trigger_type = request.args.get("trigger_type", "")
    if trigger_type:
        records = db.execute("""
            SELECT id, project_id, trigger_type, started_at, finished_at, status,
                   total_items, abnormal_items
            FROM inspection_records
            WHERE project_id=? AND trigger_type=?
            ORDER BY started_at DESC
            LIMIT 50
        """, (project_id, trigger_type)).fetchall()
    else:
        records = db.execute("""
            SELECT id, project_id, trigger_type, started_at, finished_at, status,
                   total_items, abnormal_items
            FROM inspection_records
            WHERE project_id=?
            ORDER BY started_at DESC
            LIMIT 50
        """, (project_id,)).fetchall()
    return jsonify([dict(r) for r in records])


@app.route("/api/records/<int:record_id>", methods=["GET"])
def get_record(record_id):
    db = get_db()
    record = db.execute("SELECT * FROM inspection_records WHERE id=?", (record_id,)).fetchone()
    if not record:
        return jsonify({"error": "记录不存在"}), 404
    return jsonify(dict(record))


@app.route("/api/records/<int:record_id>", methods=["DELETE"])
def delete_record(record_id):
    db = get_db()
    record = db.execute("SELECT id FROM inspection_records WHERE id=?", (record_id,)).fetchone()
    if not record:
        return jsonify({"error": "记录不存在"}), 404
    db.execute("DELETE FROM inspection_details WHERE record_id=?", (record_id,))
    db.execute("DELETE FROM inspection_records WHERE id=?", (record_id,))
    db.commit()
    return jsonify({"message": "删除成功"})


@app.route("/api/records/<int:record_id>/report", methods=["GET"])
def get_report(record_id):
    format_type = request.args.get("format", "html")
    db = get_db()
    record = db.execute("SELECT * FROM inspection_records WHERE id=?", (record_id,)).fetchone()
    if not record:
        return jsonify({"error": "记录不存在"}), 404

    if format_type == "html":
        return record["report_html"] or "", 200, {"Content-Type": "text/html; charset=utf-8"}
    elif format_type == "markdown":
        return record["report_markdown"] or "", 200, {"Content-Type": "text/plain; charset=utf-8"}
    elif format_type == "json":
        details = db.execute(
            "SELECT * FROM inspection_details WHERE record_id=?", (record_id,)
        ).fetchall()
        return jsonify({
            "summary": json.loads(record["summary_json"] or "{}"),
            "details": [dict(d) for d in details]
        })
    else:
        return jsonify({"error": f"不支持的格式: {format_type}"}), 400


@app.route("/api/records/<int:record_id>/preview", methods=["GET"])
def preview_report(record_id):
    db = get_db()
    record = db.execute("SELECT * FROM inspection_records WHERE id=?", (record_id,)).fetchone()
    if not record:
        return jsonify({"error": "记录不存在"}), 404
    return jsonify({
        "html": record["report_html"] or "",
        "markdown": record["report_markdown"] or "",
        "summary": json.loads(record["summary_json"] or "{}")
    })


@app.route("/api/records/<int:record_id>/details", methods=["GET"])
def get_record_details(record_id):
    db = get_db()
    details = db.execute(
        "SELECT * FROM inspection_details WHERE record_id=?", (record_id,)
    ).fetchall()
    return jsonify([dict(d) for d in details])


# ==================== 报告推送 ====================

@app.route("/api/records/<int:record_id>/send", methods=["POST"])
def send_report(record_id):
    """发送报告到项目的所有启用通知渠道"""
    db = get_db()
    record = db.execute("SELECT * FROM inspection_records WHERE id=?", (record_id,)).fetchone()
    if not record:
        return jsonify({"error": "记录不存在"}), 404

    channels = db.execute(
        "SELECT * FROM notification_channels WHERE project_id=? AND enabled=1",
        (record["project_id"],)
    ).fetchall()

    if not channels:
        return jsonify({"error": "没有启用的通知渠道"}), 400

    results = []
    project = db.execute("SELECT name FROM projects WHERE id=?", (record["project_id"],)).fetchone()
    project_name = project["name"] if project else f"项目#{record['project_id']}"
    for ch in channels:
        result = _send_to_channel(ch, record, request.host_url, project_name)
        results.append(result)
    return jsonify({"results": results})


@app.route("/api/records/<int:record_id>/send/<int:channel_id>", methods=["POST"])
def send_report_to_channel(record_id, channel_id):
    """发送报告到指定通知渠道"""
    db = get_db()
    record = db.execute("SELECT * FROM inspection_records WHERE id=?", (record_id,)).fetchone()
    if not record:
        return jsonify({"error": "记录不存在"}), 404

    channel = db.execute(
        "SELECT * FROM notification_channels WHERE id=? AND project_id=?",
        (channel_id, record["project_id"])
    ).fetchone()
    if not channel:
        return jsonify({"error": "通知渠道不存在"}), 404

    project = db.execute("SELECT name FROM projects WHERE id=?", (record["project_id"],)).fetchone()
    project_name = project["name"] if project else f"项目#{record['project_id']}"
    result = _send_to_channel(channel, record, request.host_url, project_name)
    return jsonify(result)


def _send_to_channel(channel, record, base_url="", project_name=""):
    """Send report to a single notification channel"""
    config = json.loads(channel["config_json"])
    channel_type = channel["channel_type"]
    record_id = record["id"]
    channel_id = channel["id"]
    project_id = channel["project_id"]
    report_format = channel["report_format"] or "markdown"

    # Validate required config fields
    required_keys = {"feishu": ["webhook_url"], "email": ["smtp_host", "smtp_port", "to"]}
    missing = [k for k in required_keys.get(channel_type, []) if not config.get(k)]
    if missing:
        err = f"缺少必填配置: {', '.join(missing)}"
        _log_notification(record_id, channel_id, channel_type, project_id, "failed", err)
        return {"channel_id": channel["id"], "channel_type": channel_type,
                "status": "failed", "error": err}

    report_content = record["report_markdown"] or record["report_html"] or ""

    try:
        if channel_type == "feishu":
            from notifiers.feishu import FeishuNotifier
            notifier = FeishuNotifier(config["webhook_url"])
            if report_format == "feishu_card":
                summary = json.loads(record["summary_json"] or "{}")
                summary["inspection_time"] = record["started_at"] if "started_at" in record.keys() else "-"
                summary["abnormal_items"] = record["abnormal_items"] if "abnormal_items" in record.keys() else 0
                notifier.send_card_report(
                    title=f"巡检报告 - {project_name}",
                    summary=summary,
                    record_id=record_id,
                    project_name=project_name,
                    base_url=base_url
                )
            elif report_format == "json":
                summary = json.loads(record["summary_json"] or "{}")
                summary["report_url"] = f"/api/records/{record_id}/report"
                notifier.send_json(summary)
            elif report_format == "html":
                notifier.send("巡检报告", report_content[:2000], "html")
            else:
                notifier.send_report(report_content, report_format)

        elif channel_type == "email":
            from notifiers.email import EmailNotifier
            notifier = EmailNotifier(
                config["smtp_host"], int(config.get("smtp_port", 465)),
                config.get("username", ""), config.get("password", ""),
                config.get("smtp_ssl", True)
            )
            to_addr = config.get("to", "")
            notifier.send("运维巡检报告",
                         record["report_html"] or report_content,
                         "html" if record["report_html"] else "markdown",
                         to_addr=to_addr)

        _log_notification(record_id, channel_id, channel_type, project_id, "success")
        return {"channel_id": channel["id"], "channel_type": channel_type,
                "status": "success", "message": "发送成功"}
    except Exception as e:
        _log_notification(record_id, channel_id, channel_type, project_id, "failed", str(e))
        return {"channel_id": channel["id"], "channel_type": channel_type,
                "status": "failed", "error": str(e)}


def _log_notification(record_id, channel_id, channel_type, project_id, status, error=None):
    try:
        db = sqlite3.connect(DB_PATH)
        now = datetime.now().isoformat()
        db.execute(
            "INSERT INTO notification_logs (record_id, channel_id, channel_type, project_id, status, error, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (record_id, channel_id, channel_type, project_id, status, error, now)
        )
        db.commit()
        db.close()
    except Exception:
        pass


# ==================== 连接测试 ====================

@app.route("/api/test/prometheus", methods=["POST"])
def test_prometheus_connection():
    data = request.json
    try:
        prom = PrometheusClient(
            url=data["url"],
            auth_enabled=data.get("auth_enabled", False),
            username=data.get("username", ""),
            password=data.get("password", "")
        )
        targets = prom.get_targets()
        count = len(targets.get("activeTargets", []))
        return jsonify({"status": "success", "target_count": count})
    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)}), 400


@app.route("/api/test/notification", methods=["POST"])
def test_notification():
    data = request.json
    channel_type = data["channel_type"]
    config = data["config"]
    project_id = data.get("project_id")
    channel_id = data.get("channel_id")
    try:
        if channel_type == "feishu":
            from notifiers.feishu import FeishuNotifier
            notifier = FeishuNotifier(config["webhook_url"])
            notifier.send("巡检系统测试", "这是一条测试消息，如果您收到说明配置正确。")
        elif channel_type == "email":
            from notifiers.email import EmailNotifier
            notifier = EmailNotifier(
                config["smtp_host"], int(config.get("smtp_port", 465)),
                config.get("username", ""), config.get("password", ""),
                config.get("smtp_ssl", True)
            )
            notifier.send("巡检系统通知测试",
                         "<h3>测试成功</h3><p>通知渠道配置正确。</p>",
                         "html",
                         to_addr=config.get("to", ""))
        if project_id and channel_id:
            _log_notification(0, channel_id, channel_type, project_id, "success")
        return jsonify({"status": "success", "message": "发送成功"})
    except Exception as e:
        if project_id and channel_id:
            _log_notification(0, channel_id, channel_type, project_id, "failed", str(e))
        return jsonify({"status": "failed", "error": str(e)}), 400


# ==================== 推送日志 ====================


@app.route("/api/projects/<int:project_id>/notification-logs", methods=["GET"])
def list_notification_logs(project_id):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM notification_logs WHERE project_id=? ORDER BY created_at DESC LIMIT 100",
        (project_id,)
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/notification-logs/<int:log_id>", methods=["DELETE"])
def delete_notification_log(log_id):
    db = get_db()
    db.execute("DELETE FROM notification_logs WHERE id=?", (log_id,))
    db.commit()
    return jsonify({"message": "删除成功"})


# ==================== 统计分析 ====================

@app.route("/api/stats/overview", methods=["GET"])
def stats_overview():
    db = get_db()
    total_projects = db.execute("SELECT COUNT(*) as cnt FROM projects").fetchone()["cnt"]
    total_records = db.execute("SELECT COUNT(*) as cnt FROM inspection_records").fetchone()["cnt"]
    recent_records = db.execute("""
        SELECT COUNT(*) as cnt FROM inspection_records
        WHERE started_at > datetime('now', '-7 days')
    """).fetchone()["cnt"]
    abnormal_today = db.execute("""
        SELECT COALESCE(SUM(abnormal_items), 0) as cnt FROM inspection_records
        WHERE started_at > datetime('now', '-1 days')
    """).fetchone()["cnt"]
    return jsonify({
        "total_projects": total_projects,
        "total_records": total_records,
        "recent_records": recent_records,
        "abnormal_today": abnormal_today
    })


# ==================== 前端静态文件 ====================

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/assets/<path:filename>")
def static_assets(filename):
    return send_from_directory(os.path.join(app.static_folder, "assets"), filename)


@app.route("/<path:path>")
def static_files(path):
    file_path = os.path.join(app.static_folder, path)
    if os.path.exists(file_path):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


# ==================== 系统设置 ====================

@app.route("/api/settings", methods=["GET"])
def get_settings():
    db = get_db()
    rows = db.execute("SELECT key, value FROM app_settings").fetchall()
    return jsonify({r["key"]: r["value"] for r in rows})


@app.route("/api/settings", methods=["PUT"])
def update_settings():
    data = request.json
    db = get_db()
    for key, value in data.items():
        if key in ("records_retention_days", "details_retention_days"):
            db.execute(
                "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
                (key, str(int(value)))
            )
    db.commit()
    return jsonify({"status": "success", "message": "设置已保存"})


# ==================== 调度器初始化 ====================

_scheduler_instance = None
_scheduler_jobs = {}


def _reload_scheduled_jobs():
    """Reload all cron jobs from the database into the scheduler"""
    global _scheduler_instance, _scheduler_jobs
    if _scheduler_instance is None:
        return
    sched = _scheduler_instance
    for sid in list(_scheduler_jobs.keys()):
        try:
            sched.remove_job(sid)
        except Exception:
            pass
    _scheduler_jobs.clear()
    try:
        db = get_db()
        rows = db.execute("""
            SELECT s.*, p.name as project_name FROM schedules s
            JOIN projects p ON s.project_id=p.id WHERE s.enabled=1
        """).fetchall()
        db.close()
        for row in rows:
            try:
                parts = row["cron_expression"].strip().split()
                if len(parts) != 5:
                    continue
                job_id = f"schedule_{row['id']}"
                pid = row["project_id"]
                sched.add_job(
                    func=lambda pid=pid: _run_scheduled_inspection(pid),
                    trigger='cron',
                    minute=parts[0], hour=parts[1], day=parts[2],
                    month=parts[3], day_of_week=parts[4],
                    id=job_id, replace_existing=True,
                    name=f"{row['project_name']} ({row['cron_expression']})"
                )
                _scheduler_jobs[job_id] = True
                print(f"Scheduled: {row['project_name']} - {row['cron_expression']}", flush=True)
            except Exception as e:
                print(f"Failed to schedule job {row['id']}: {e}", flush=True)
    except Exception as e:
        print(f"Failed to load schedules: {e}", flush=True)


def _run_scheduled_inspection(project_id):
    try:
        engine = InspectionEngine(project_id, DB_PATH, trigger_type="scheduled")
        record_id = engine.run()
        db = get_db()
        channels = db.execute(
            "SELECT * FROM notification_channels WHERE project_id=? AND enabled=1",
            (project_id,)
        ).fetchall()
        project = db.execute(
            "SELECT name FROM projects WHERE id=?", (project_id,)
        ).fetchone()
        project_name = project["name"] if project else f"项目#{project_id}"
        for ch in channels:
            record = db.execute(
                "SELECT * FROM inspection_records WHERE id=?", (record_id,)
            ).fetchone()
            if record:
                _send_to_channel(ch, record, SERVER_BASE_URL or "", project_name)
        db.close()
        print(f"Scheduled inspection completed for project {project_id}, record {record_id}", flush=True)
    except Exception as e:
        print(f"Scheduled inspection failed for project {project_id}: {e}", flush=True)


def init_scheduler(app_instance):
    global _scheduler_instance
    try:
        import warnings
        warnings.filterwarnings("ignore", category=UserWarning, module="pytz")
        from apscheduler.schedulers.background import BackgroundScheduler
        import pytz
        tz = pytz.timezone("Asia/Shanghai")
        _scheduler_instance = BackgroundScheduler(timezone=tz)

        with app_instance.app_context():
            _reload_scheduled_jobs()

        def cleanup_old_data():
            with app_instance.app_context():
                db = get_db()
                now = datetime.now()
                days_str = db.execute(
                    "SELECT value FROM app_settings WHERE key='records_retention_days'"
                ).fetchone()
                records_days = int(days_str["value"]) if days_str else 90
                cutoff = (now - timedelta(days=records_days)).isoformat()
                old = db.execute(
                    "SELECT id FROM inspection_records WHERE started_at < ?",
                    (cutoff,)
                ).fetchall()
                old_ids = [r["id"] for r in old]
                if old_ids:
                    placeholders = ",".join("?" for _ in old_ids)
                    db.execute(f"DELETE FROM inspection_details WHERE record_id IN ({placeholders})", old_ids)
                    db.execute(f"DELETE FROM inspection_records WHERE id IN ({placeholders})", old_ids)
                    print(f"Cleaned up {len(old_ids)} old inspection records", flush=True)
                log_days_str = db.execute(
                    "SELECT value FROM app_settings WHERE key='details_retention_days'"
                ).fetchone()
                log_days = int(log_days_str["value"]) if log_days_str else 90
                cutoff = (now - timedelta(days=log_days)).isoformat()
                db.execute(
                    "DELETE FROM notification_logs WHERE created_at < ?",
                    (cutoff,)
                )
                db.commit()
                db.close()

        _scheduler_instance.add_job(cleanup_old_data, 'interval', hours=24,
                                    id='data_cleanup', replace_existing=True)
        _scheduler_instance.add_job(_reload_scheduled_jobs, 'interval', minutes=5,
                                    id='schedule_reload', replace_existing=True)
        _scheduler_instance.start()
        return _scheduler_instance
    except Exception as e:
        print(f"Scheduler not started: {e}")
        return None


# ==================== 入口 ====================

if __name__ == "__main__":
    init_db()
    sched = init_scheduler(app)
    try:
        app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
    finally:
        if sched:
            sched.shutdown()