"""Feishu (飞书) bot notifier"""
import requests
from notifiers.base import BaseNotifier


class FeishuNotifier(BaseNotifier):
    """飞书机器人通知 (使用 interactive card 格式)"""

    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    def send(self, title, content, content_type="markdown"):
        payload = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {"title": {"tag": "plain_text", "content": title}},
                "elements": [{"tag": "markdown", "content": content[:30000]}]
            }
        }
        resp = requests.post(self.webhook_url, json=payload, timeout=15)
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") != 0:
            raise Exception(f"飞书API错误: {result.get('msg', 'unknown')}")
        return result

    def send_report(self, report_content, format_type="markdown"):
        return self.send("巡检报告 Report", report_content, format_type)

    def send_card_report(self, title, summary, record_id, project_name="项目", base_url=""):
        """Send a structured card report with rich formatting"""
        elements = []

        # Status overview
        total = summary.get("total_items", 0)
        normal = summary.get("normal_items", 0)
        abnormal = summary.get("abnormal_items", 0)
        health = summary.get("health_score", 0)
        up = summary.get("up_targets", 0)
        down = summary.get("down_targets", 0)
        critical = summary.get("critical_items", 0)
        warning = summary.get("warning_items", 0)

        status_color = "green" if health >= 80 else "orange" if health >= 60 else "red"

        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**项目**: {project_name}\n**健康状况**: **<font color='{status_color}'>{health}分</font>**\n**巡检时间**: {summary.get('inspection_time', '-')}"
            }
        })

        elements.append({"tag": "hr"})

        # Stats grid
        elements.append({
            "tag": "div",
            "fields": [
                {"is_short": True, "text": {"tag": "lark_md", "content": f"巡检项\n{total} 项"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"正常\n{normal} 项"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"异常\n{abnormal} 项"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"严重\n{critical} 项"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"警告\n{warning} 项"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"健康分\n{health} 分"}},
            ]
        })

        elements.append({"tag": "hr"})

        # Target status
        elements.append({
            "tag": "div",
            "fields": [
                {"is_short": True, "text": {"tag": "lark_md", "content": f"在线\n{up} 个"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"离线\n{down} 个"}},
            ]
        })

        # View report button
        report_url = f"{base_url}api/records/{record_id}/report"
        elements.append({
            "tag": "action",
            "actions": [{
                "tag": "button",
                "text": {"tag": "plain_text", "content": "查看完整报告"},
                "type": "primary",
                "multi_url": {
                    "url": report_url,
                    "pc_url": report_url,
                    "android_url": report_url,
                    "ios_url": report_url
                }
            }]
        })

        payload = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    "template": status_color
                },
                "elements": elements
            }
        }
        resp = requests.post(self.webhook_url, json=payload, timeout=15)
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") != 0:
            raise Exception(f"飞书API错误: {result.get('msg', 'unknown')}")
        return result

    def send_json(self, data):
        items = []
        for k, v in data.items():
            items.append({"tag": "markdown", "content": f"**{k}**: {v}"})

        payload = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {"title": {"tag": "plain_text", "content": "巡检报告 (结构化数据)"}},
                "elements": items
            }
        }
        resp = requests.post(self.webhook_url, json=payload, timeout=15)
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") != 0:
            raise Exception(f"飞书API错误: {result.get('msg', 'unknown')}")
        return result