"""cAdvisor plugin - container metrics"""
from plugins.base import BasePlugin


class CadvisorPlugin(BasePlugin):
    """Docker容器监控插件"""

    def inspect(self, instance) -> list:
        results = []
        instance_addr = instance["instance"]

        # Container CPU
        cpu_query = f'sum(rate(container_cpu_usage_seconds_total{{instance="{instance_addr}"}}[5m])) by (container_label_com_docker_compose_service, name) * 100'
        try:
            cpu_data = self.prom.query(cpu_query)
            for r in cpu_data.get("result", []):
                container = r["metric"].get("name") or r["metric"].get("container_label_com_docker_compose_service", "unknown")
                cpu_val = float(r["value"][1])
                threshold = self.thresholds.get("container_cpu_percent", 80)
                status = self._check_threshold("container_cpu_percent", cpu_val,
                                               critical_val=threshold)
                results.append(self._build_result(
                    f"容器CPU({container})", f"{cpu_val:.1f}%", f"{threshold}%", status
                ))
        except Exception as e:
            results.append(self._build_result("容器CPU", str(e), "-", "严重", "查询失败"))

        # Container Memory
        mem_query = f'sum(container_memory_working_set_bytes{{instance="{instance_addr}"}}) by (name)'
        try:
            mem_data = self.prom.query(mem_query)
            for r in mem_data.get("result", []):
                container = r["metric"].get("name", "unknown")
                mem_val = float(r["value"][1]) / (1024 * 1024)
                threshold = self.thresholds.get("container_memory_mb", 1024)
                status = self._check_threshold("container_memory_mb", mem_val,
                                               critical_val=threshold)
                results.append(self._build_result(
                    f"容器内存({container})", f"{mem_val:.0f}MB", f"{threshold}MB", status
                ))
        except Exception as e:
            results.append(self._build_result("容器内存", str(e), "-", "严重", "查询失败"))

        return results