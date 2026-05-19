"""Generic plugin - for any Prometheus metric"""
from plugins.base import BasePlugin


class GenericPlugin(BasePlugin):
    """通用巡检插件 - 支持自定义PromQL查询"""

    def inspect(self, instance) -> list:
        results = []
        instance_addr = instance["instance"]

        queries = self.extra_config.get("queries", [])
        for q in queries:
            name = q.get("name", "unknown")
            promql = q.get("promql", "").replace("{instance}", instance_addr)
            threshold = q.get("threshold")
            severity = q.get("severity", "critical")

            if not promql:
                continue

            try:
                data = self.prom.query(promql)
                if data.get("result"):
                    for r in data["result"]:
                        val = float(r["value"][1])
                        if threshold is not None and val >= float(threshold):
                            results.append(self._build_result(
                                name, f"{val:.2f}", str(threshold), severity
                            ))
                        else:
                            results.append(self._build_result(
                                name, f"{val:.2f}", str(threshold) if threshold else "-",
                                "正常"
                            ))
            except Exception as e:
                results.append(self._build_result(
                    name, str(e), str(threshold) if threshold else "-", "严重", "查询失败"
                ))

        return results