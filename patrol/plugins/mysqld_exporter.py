"""MySQL Exporter plugin"""
from plugins.base import BasePlugin


class MySQLExporterPlugin(BasePlugin):
    """MySQL数据库巡检插件"""

    def inspect(self, instance) -> list:
        results = []
        instance_addr = instance["instance"]

        # Connections
        conn_query = f'max(mysql_global_status_threads_connected{{instance="{instance_addr}"}})'
        conn_limit_query = f'max(mysql_global_variables_max_connections{{instance="{instance_addr}"}})'
        try:
            conn_data = self.prom.query(conn_query)
            conn_limit_data = self.prom.query(conn_limit_query)
            if conn_data.get("result") and conn_limit_data.get("result"):
                conn_val = float(conn_data["result"][0]["value"][1])
                conn_limit = float(conn_limit_data["result"][0]["value"][1])
                usage_pct = (conn_val / conn_limit) * 100 if conn_limit > 0 else 0
                threshold = self.thresholds.get("connections_usage_percent", 80)
                status = self._check_threshold("connections_usage_percent", usage_pct,
                                               critical_val=threshold)
                results.append(self._build_result(
                    "连接使用率", f"{usage_pct:.1f}% ({conn_val:.0f}/{conn_limit:.0f})",
                    f"{threshold}%", status
                ))
        except Exception as e:
            results.append(self._build_result("连接数", str(e), "-", "严重", "查询失败"))

        # Slow Queries
        slow_query = f'rate(mysql_global_status_slow_queries{{instance="{instance_addr}"}}[5m])'
        try:
            slow_data = self.prom.query(slow_query)
            if slow_data.get("result"):
                slow_val = float(slow_data["result"][0]["value"][1])
                threshold = self.thresholds.get("slow_queries_per_min", 10)
                status = self._check_threshold("slow_queries_per_min", slow_val,
                                               critical_val=threshold)
                results.append(self._build_result(
                    "慢查询速率", f"{slow_val:.2f}/秒", f"{threshold}/秒", status
                ))
        except Exception as e:
            results.append(self._build_result("慢查询", str(e), "-", "严重", "查询失败"))

        # Replication Lag
        lag_query = f'mysql_slave_status_seconds_behind_master{{instance="{instance_addr}"}}'
        try:
            lag_data = self.prom.query(lag_query)
            for r in lag_data.get("result", []):
                lag_val = float(r["value"][1])
                threshold = self.thresholds.get("replication_lag_seconds", 30)
                status = self._check_threshold("replication_lag_seconds", lag_val,
                                               critical_val=threshold)
                results.append(self._build_result(
                    "主从延迟", f"{lag_val:.0f}秒", f"{threshold}秒", status
                ))
        except Exception as e:
            pass  # Replication might not be configured

        return results