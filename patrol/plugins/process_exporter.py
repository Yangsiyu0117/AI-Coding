"""Process Exporter plugin"""
from plugins.base import BasePlugin


class ProcessExporterPlugin(BasePlugin):
    """进程监控巡检插件"""

    def inspect(self, instance) -> list:
        results = []
        instance_addr = instance["instance"]

        # Process count
        proc_query = f'process_num_threads{{instance="{instance_addr}"}}'
        try:
            proc_data = self.prom.query(proc_query)
            if proc_data.get("result"):
                for r in proc_data["result"]:
                    proc_name = r["metric"].get("process", "unknown")
                    proc_value = float(r["value"][1])
                    results.append(self._build_result(
                        f"进程线程数({proc_name})", f"{proc_value:.0f}", "-",
                        "正常" if proc_value > 0 else "严重",
                        f"进程 {proc_name} 异常" if proc_value == 0 else ""
                    ))
        except Exception as e:
            results.append(self._build_result("进程状态", str(e), "-", "严重", "查询失败"))

        return results