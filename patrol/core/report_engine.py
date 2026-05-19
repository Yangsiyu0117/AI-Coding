"""Multi-format report generation engine"""
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
import json
import os


class ReportEngine:
    """多格式报告生成引擎"""

    def __init__(self, templates_dir=None):
        if templates_dir is None:
            templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
        self.env = Environment(loader=FileSystemLoader(templates_dir))
        self.env.filters["severity_emoji"] = self._severity_emoji
        self.env.filters["severity_color"] = self._severity_color
        self.env.filters["format_datetime"] = self._format_datetime

    def generate(self, context: dict) -> dict:
        context["statistics"] = self._calculate_statistics(context)

        return {
            "html": self._render_html(context),
            "markdown": self._render_markdown(context),
            "text": self._render_text(context),
            "json": self._render_json(context),
        }

    def _render_html(self, context):
        template = self.env.get_template("report.html.j2")
        return template.render(**context)

    def _render_markdown(self, context):
        template = self.env.get_template("report.md.j2")
        return template.render(**context)

    def _render_text(self, context):
        template = self.env.get_template("report.txt.j2")
        return template.render(**context)

    def _render_json(self, context):
        return json.dumps({
            "project": context["project_name"],
            "env": context["env"],
            "timestamp": context["timestamp"].isoformat() if isinstance(context["timestamp"], datetime) else str(context["timestamp"]),
            "statistics": context["statistics"],
            "abnormal_items": [
                item for item in context["inspection_results"]
                if item.get("status") != "正常"
            ],
            "active_alerts": context.get("active_alerts", [])
        }, ensure_ascii=False, indent=2)

    def _calculate_statistics(self, context):
        results = context.get("inspection_results", [])
        targets = context.get("targets_summary", {})

        total_targets = sum(len(t) for t in targets.values())
        up_targets = sum(
            1 for ts in targets.values()
            for t in ts if isinstance(t, dict) and t.get("state") == "up"
        )

        total_items = len(results)
        normal_items = sum(1 for r in results if r.get("status") == "正常")
        warning_items = sum(1 for r in results if r.get("status") == "警告")
        critical_items = sum(1 for r in results if r.get("status") == "严重")

        return {
            "total_targets": total_targets,
            "up_targets": up_targets,
            "down_targets": total_targets - up_targets,
            "total_items": total_items,
            "normal_items": normal_items,
            "warning_items": warning_items,
            "critical_items": critical_items,
            "health_score": round(normal_items / total_items * 100, 1) if total_items > 0 else 100
        }

    @staticmethod
    def _severity_emoji(status):
        return {"正常": "✅", "警告": "⚠️", "严重": "🔴"}.get(status, "❓")

    @staticmethod
    def _severity_color(status):
        return {"正常": "#52c41a", "警告": "#faad14", "严重": "#ff4d4f"}.get(status, "#999")

    @staticmethod
    def _format_datetime(dt):
        if isinstance(dt, datetime):
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        return str(dt)