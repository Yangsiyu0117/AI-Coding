"""Pulsar plugin"""
from plugins.base import BasePlugin


class PulsarPlugin(BasePlugin):
    """Apache Pulsar消息队列巡检插件"""

    def inspect(self, instance) -> list:
        results = []
        instance_addr = instance["instance"]

        # Message backlog
        backlog_query = f'sum(pulsar_subscription_back_log{{instance="{instance_addr}"}}) by (topic, subscription)'
        try:
            backlog_data = self.prom.query(backlog_query)
            for r in backlog_data.get("result", []):
                backlog_val = float(r["value"][1])
                topic = r["metric"].get("topic", "unknown")
                sub = r["metric"].get("subscription", "unknown")
                threshold = self.thresholds.get("backlog_threshold", 10000)
                status = self._check_threshold("backlog_threshold", backlog_val,
                                               critical_val=threshold)
                results.append(self._build_result(
                    f"消息积压({topic}/{sub})", f"{backlog_val:.0f}", f"{threshold}", status
                ))
        except Exception as e:
            results.append(self._build_result("消息积压", str(e), "-", "严重", "查询失败"))

        # Rate in/out
        rate_in_query = f'rate(pulsar_broker_publish_rate{{instance="{instance_addr}"}}[5m])'
        try:
            rate_data = self.prom.query(rate_in_query)
            if rate_data.get("result"):
                total_rate = sum(float(r["value"][1]) for r in rate_data["result"])
                results.append(self._build_result(
                    "消息生产速率", f"{total_rate:.1f} msg/s", "-", "正常"
                ))
        except Exception as e:
            pass

        return results