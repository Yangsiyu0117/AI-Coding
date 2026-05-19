"""Redis Exporter plugin"""
from plugins.base import BasePlugin


class RedisExporterPlugin(BasePlugin):
    """Redis缓存巡检插件"""

    def inspect(self, instance) -> list:
        results = []
        instance_addr = instance["instance"]

        # Memory Usage
        mem_query = f'redis_memory_used_bytes{{instance="{instance_addr}"}}'
        mem_max_query = f'redis_memory_max_bytes{{instance="{instance_addr}"}}'
        try:
            mem_data = self.prom.query(mem_query)
            if mem_data.get("result"):
                mem_val = float(mem_data["result"][0]["value"][1])
                mem_max_data = self.prom.query(mem_max_query)
                if mem_max_data.get("result"):
                    mem_max = float(mem_max_data["result"][0]["value"][1])
                    usage_pct = (mem_val / mem_max) * 100 if mem_max > 0 else 0
                else:
                    usage_pct = (mem_val / (1024 * 1024 * 1024)) * 100  # assume 1GB max
                    mem_max = 1024 * 1024 * 1024

                threshold = self.thresholds.get("memory_usage_percent", 80)
                status = self._check_threshold("memory_usage_percent", usage_pct,
                                               critical_val=threshold)
                mem_mb = mem_val / (1024 * 1024)
                max_mb = mem_max / (1024 * 1024)
                results.append(self._build_result(
                    "内存使用率", f"{usage_pct:.1f}% ({mem_mb:.0f}MB/{max_mb:.0f}MB)",
                    f"{threshold}%", status
                ))
        except Exception as e:
            results.append(self._build_result("内存使用", str(e), "-", "严重", "查询失败"))

        # Connected Clients
        clients_query = f'redis_connected_clients{{instance="{instance_addr}"}}'
        try:
            clients_data = self.prom.query(clients_query)
            if clients_data.get("result"):
                clients_val = float(clients_data["result"][0]["value"][1])
                threshold = self.thresholds.get("connected_clients", 500)
                status = self._check_threshold("connected_clients", clients_val,
                                               critical_val=threshold)
                results.append(self._build_result(
                    "连接数", f"{clients_val:.0f}", f"{threshold}", status
                ))
        except Exception as e:
            results.append(self._build_result("连接数", str(e), "-", "严重", "查询失败"))

        # Hit Rate
        hits_query = f'rate(redis_keyspace_hits_total{{instance="{instance_addr}"}}[5m])'
        misses_query = f'rate(redis_keyspace_misses_total{{instance="{instance_addr}"}}[5m])'
        try:
            hits_data = self.prom.query(hits_query)
            misses_data = self.prom.query(misses_query)
            hits_val = float(hits_data["result"][0]["value"][1]) if hits_data.get("result") else 0
            misses_val = float(misses_data["result"][0]["value"][1]) if misses_data.get("result") else 0
            total = hits_val + misses_val
            hit_rate = (hits_val / total * 100) if total > 0 else 100
            threshold = self.thresholds.get("hit_rate_percent", 95)
            status = self._check_threshold("hit_rate_percent", 100 - hit_rate,
                                           critical_val=(100 - threshold))
            results.append(self._build_result(
                "缓存命中率", f"{hit_rate:.1f}%", f">{threshold}%", status
            ))
        except Exception as e:
            results.append(self._build_result("缓存命中率", str(e), "-", "严重", "查询失败"))

        return results