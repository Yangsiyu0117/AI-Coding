"""Elasticsearch Exporter plugin"""
from plugins.base import BasePlugin


class ElasticsearchPlugin(BasePlugin):
    """Elasticsearch集群巡检插件"""

    def inspect(self, instance) -> list:
        results = []
        instance_addr = instance["instance"]

        # Cluster Status
        status_query = f'elasticsearch_cluster_health_status{{instance="{instance_addr}"}}'
        try:
            status_data = self.prom.query(status_query)
            for r in status_data.get("result", []):
                status_val = int(r["value"][1])
                status_map = {0: "green", 1: "yellow", 2: "red"}
                status_text = status_map.get(status_val, f"unknown({status_val})")
                item_status = "正常" if status_val == 0 else ("警告" if status_val == 1 else "严重")
                results.append(self._build_result(
                    "集群健康状态", status_text, "green(0)", item_status
                ))
        except Exception as e:
            results.append(self._build_result("集群状态", str(e), "-", "严重", "查询失败"))

        # Nodes count
        nodes_query = f'elasticsearch_cluster_health_number_of_nodes{{instance="{instance_addr}"}}'
        try:
            nodes_data = self.prom.query(nodes_query)
            if nodes_data.get("result"):
                nodes_val = float(nodes_data["result"][0]["value"][1])
                results.append(self._build_result(
                    "节点数", f"{nodes_val:.0f}", "-", "正常" if nodes_val > 0 else "严重"
                ))
        except Exception as e:
            results.append(self._build_result("节点数", str(e), "-", "严重", "查询失败"))

        # JVM Heap Usage
        jvm_query = f'elasticsearch_jvm_memory_heap_used_percent{{instance="{instance_addr}"}}'
        try:
            jvm_data = self.prom.query(jvm_query)
            if jvm_data.get("result"):
                jvm_val = float(jvm_data["result"][0]["value"][1])
                threshold = self.thresholds.get("jvm_heap_percent", 85)
                status = self._check_threshold("jvm_heap_percent", jvm_val,
                                               critical_val=threshold)
                results.append(self._build_result(
                    "JVM堆内存", f"{jvm_val:.1f}%", f"{threshold}%", status
                ))
        except Exception as e:
            results.append(self._build_result("JVM堆内存", str(e), "-", "严重", "查询失败"))

        return results