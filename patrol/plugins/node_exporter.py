"""Node Exporter plugin - system metrics inspection"""
from plugins.base import BasePlugin


class NodeExporterPlugin(BasePlugin):
    """系统指标巡检插件 (CPU/内存/磁盘/网络/负载)"""

    def inspect(self, instance) -> list:
        results = []
        instance_addr = instance["instance"]

        # CPU Usage
        cpu_query = f'100 - (avg by(instance)(rate(node_cpu_seconds_total{{instance="{instance_addr}",mode="idle"}}[5m])) * 100)'
        try:
            cpu_data = self.prom.query(cpu_query)
            if cpu_data.get("result"):
                cpu_value = float(cpu_data["result"][0]["value"][1])
                threshold = self.thresholds.get("cpu_usage_percent", 85)
                status = self._check_threshold("cpu_usage_percent", cpu_value,
                                               critical_val=threshold)
                results.append(self._build_result(
                    "CPU使用率", f"{cpu_value:.1f}%", f"{threshold}%", status
                ))
        except Exception as e:
            results.append(self._build_result("CPU使用率", str(e), "-", "严重", "查询失败"))

        # Memory Usage
        mem_query = f'100 * (1 - (node_memory_MemAvailable_bytes{{instance="{instance_addr}"}} / node_memory_MemTotal_bytes{{instance="{instance_addr}"}}))'
        try:
            mem_data = self.prom.query(mem_query)
            if mem_data.get("result"):
                mem_value = float(mem_data["result"][0]["value"][1])
                threshold = self.thresholds.get("memory_usage_percent", 85)
                status = self._check_threshold("memory_usage_percent", mem_value,
                                               critical_val=threshold)
                results.append(self._build_result(
                    "内存使用率", f"{mem_value:.1f}%", f"{threshold}%", status
                ))
        except Exception as e:
            results.append(self._build_result("内存使用率", str(e), "-", "严重", "查询失败"))

        # Disk Usage
        disk_query = f'100 * (node_filesystem_size_bytes{{instance="{instance_addr}",fstype!="",mountpoint!=""}} - node_filesystem_free_bytes{{instance="{instance_addr}",fstype!="",mountpoint!=""}}) / node_filesystem_size_bytes{{instance="{instance_addr}",fstype!="",mountpoint!=""}}'
        try:
            disk_data = self.prom.query(disk_query)
            for result in disk_data.get("result", []):
                mount = result["metric"].get("mountpoint", "unknown")
                disk_value = float(result["value"][1])
                threshold = self.thresholds.get("disk_usage_percent", 90)
                status = self._check_threshold("disk_usage_percent", disk_value,
                                               critical_val=threshold)
                results.append(self._build_result(
                    f"磁盘使用率({mount})", f"{disk_value:.1f}%", f"{threshold}%", status
                ))
        except Exception as e:
            results.append(self._build_result("磁盘使用率", str(e), "-", "严重", "查询失败"))

        # Load Average (1m)
        load_query = f'node_load1{{instance="{instance_addr}"}}'
        try:
            load_data = self.prom.query(load_query)
            if load_data.get("result"):
                load_value = float(load_data["result"][0]["value"][1])
                cpu_count_query = f'count(node_cpu_seconds_total{{instance="{instance_addr}",mode="idle"}})'
                cpu_count_data = self.prom.query(cpu_count_query)
                cpu_count = 1
                if cpu_count_data.get("result"):
                    cpu_count = len(cpu_count_data["result"])
                load_pct = (load_value / cpu_count) * 100
                threshold = self.thresholds.get("load_percent", cpu_count * 0.7 * 100 / cpu_count)
                status = self._check_threshold("load_percent", load_pct,
                                               critical_val=threshold)
                results.append(self._build_result(
                    "系统负载(1m)", f"{load_value:.2f}", f"CPU核心数: {cpu_count}", status
                ))
        except Exception as e:
            results.append(self._build_result("系统负载", str(e), "-", "严重", "查询失败"))

        return results