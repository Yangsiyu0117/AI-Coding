"""Inspection execution engine"""
import json
import os
import sqlite3
import traceback
from datetime import datetime
from core.datasource import DataSourceConfig, get_default_registry
from core.discovery import TargetDiscovery
from core.filter import InstanceFilter
from core.plugin_loader import PluginLoader
from core.report_engine import ReportEngine


class InspectionEngine:
    """巡检执行引擎 - 核心调度器"""

    def __init__(self, project_id, db_path, trigger_type="manual"):
        self.project_id = project_id
        self.db_path = db_path
        self.trigger_type = trigger_type
        self.plugin_loader = PluginLoader()
        self.report_engine = ReportEngine()

    def _get_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def run(self):
        """Execute full inspection cycle"""
        db = self._get_db()

        # 1. Get project info and plugin configs
        project = db.execute("SELECT * FROM projects WHERE id=?",
                           (self.project_id,)).fetchone()
        if not project:
            raise ValueError(f"Project {self.project_id} not found")

        plugin_configs = db.execute(
            "SELECT * FROM plugin_configs WHERE project_id=? AND enabled=1",
            (self.project_id,)
        ).fetchall()

        # 2. Create inspection record
        started_at = datetime.now()
        record_cursor = db.execute("""
            INSERT INTO inspection_records (project_id, trigger_type, started_at, status)
            VALUES (?, ?, ?, 'running')
        """, (self.project_id, self.trigger_type, started_at.isoformat()))
        record_id = record_cursor.lastrowid
        db.commit()

        # 3. Create data sources
        registry = get_default_registry()
        default_ds_config = DataSourceConfig.from_project(project)
        default_datasource = registry.create(default_ds_config)

        # Load per-plugin datasource overrides
        ds_rows = db.execute(
            "SELECT * FROM datasource_configs WHERE project_id=?",
            (self.project_id,)
        ).fetchall()
        datasource_map = {}
        for ds_row in ds_rows:
            try:
                cfg = DataSourceConfig(
                    ds_type=ds_row["ds_type"],
                    url=ds_row["url"],
                    auth_enabled=bool(ds_row["auth_enabled"]),
                    username=ds_row["auth_username"] or "",
                    password=ds_row["auth_password"] or "",
                    headers=json.loads(ds_row["headers_json"] or "{}")
                )
                datasource_map[ds_row["id"]] = registry.create(cfg)
            except Exception:
                pass

        # 4. Discover targets (use default datasource)
        discovery = TargetDiscovery(default_datasource)
        all_jobs = discovery.discover_jobs()

        # 5. Execute each plugin
        all_results = []
        targets_summary = {}

        for config in plugin_configs:
            plugin_name = config["plugin_name"]
            job_pattern = config["job_pattern"]
            thresholds = json.loads(config["thresholds_json"] or "{}")
            extra_config = json.loads(config["extra_config_json"] or "{}")
            filter_config = json.loads(config["filter_config_json"] or "{}") if "filter_config_json" in config.keys() else {}

            # Determine datasource for this plugin
            ds_id = config["datasource_id"] if "datasource_id" in config.keys() else None
            plugin_ds = datasource_map.get(ds_id, default_datasource)

            # Match jobs
            matched = discovery.match_jobs_by_pattern(all_jobs, job_pattern)
            if not matched:
                continue

            # Apply instance filter
            inst_filter = InstanceFilter(filter_config)
            for job_name in list(matched.keys()):
                matched[job_name]["instances"] = inst_filter.filter_instances(matched[job_name]["instances"])
                if not matched[job_name]["instances"]:
                    del matched[job_name]

            if not matched:
                continue

            # Get plugin instance
            plugin_class = self.plugin_loader.get_plugin_class(plugin_name)
            if not plugin_class:
                continue

            plugin = plugin_class(datasource=plugin_ds, thresholds=thresholds, extra_config=extra_config)

            for job_name, job_info in matched.items():
                for instance in job_info["instances"]:
                    try:
                        results = plugin.inspect(instance)
                        for r in results:
                            r["plugin_name"] = plugin_name
                            r["target_instance"] = instance["instance"]
                            all_results.append(r)
                    except Exception as e:
                        all_results.append({
                            "plugin_name": plugin_name,
                            "target_instance": instance["instance"],
                            "metric_name": "execution",
                            "current_value": str(e),
                            "threshold_value": "-",
                            "status": "严重",
                            "detail": f"插件执行异常: {traceback.format_exc()}"
                        })

            targets_summary[plugin_name] = [
                {"instance": inst["instance"], "state": inst["health"]}
                for inst in job_info["instances"]
            ]

        # 6. Get active alerts
        try:
            active_alerts = default_datasource.get_alerts()
        except Exception:
            active_alerts = []

        # 7. Generate reports
        context = {
            "project_name": project["name"],
            "env": project["env"],
            "timestamp": started_at,
            "targets_summary": targets_summary,
            "inspection_results": all_results,
            "active_alerts": active_alerts
        }

        reports = self.report_engine.generate(context)

        # 8. Calculate statistics
        total_items = len(all_results)
        abnormal_items = sum(1 for r in all_results if r.get("status") != "正常")

        # 9. Save results
        for r in all_results:
            db.execute("""
                INSERT INTO inspection_details
                (record_id, plugin_name, target_instance, metric_name,
                 current_value, threshold_value, status, detail)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (record_id, r["plugin_name"], r["target_instance"],
                  r.get("metric_name", ""), str(r.get("current_value", "")),
                  str(r.get("threshold_value", "")), r.get("status", "正常"),
                  r.get("detail", "")))

        finished_at = datetime.now()
        db.execute("""
            UPDATE inspection_records SET
                finished_at=?, status='success',
                report_html=?, report_markdown=?,
                summary_json=?, total_items=?, abnormal_items=?
            WHERE id=?
        """, (finished_at.isoformat(),
              reports.get("html", ""), reports.get("markdown", ""),
              json.dumps(context.get("statistics", {}), ensure_ascii=False),
              total_items, abnormal_items, record_id))
        db.commit()
        db.close()

        return record_id