"""APISIX plugin"""
from plugins.base import BasePlugin


class ApisixPlugin(BasePlugin):
    """APISIX网关巡检插件"""

    def inspect(self, instance) -> list:
        results = []
        instance_addr = instance["instance"]

        # HTTP status codes (error rate)
        error_query = f'sum(rate(apisix_http_status{{instance="{instance_addr}",status=~"5.."}}[5m])) / sum(rate(apisix_http_status{{instance="{instance_addr}"}}[5m])) * 100'
        try:
            error_data = self.prom.query(error_query)
            if error_data.get("result"):
                error_rate = float(error_data["result"][0]["value"][1])
                threshold = self.thresholds.get("error_rate_percent", 5)
                status = self._check_threshold("error_rate_percent", error_rate,
                                               critical_val=threshold)
                results.append(self._build_result(
                    "5xx错误率", f"{error_rate:.2f}%", f"{threshold}%", status
                ))
        except Exception as e:
            results.append(self._build_result("错误率", str(e), "-", "严重", "查询失败"))

        # Request latency
        latency_query = f'apisix_http_latency_bucket{{instance="{instance_addr}",type="request"}}'
        try:
            latency_data = self.prom.query(latency_query)
            if latency_data.get("result"):
                results.append(self._build_result(
                    "请求延迟", "数据已采集", "-", "正常"
                ))
        except Exception as e:
            pass

        # QPS
        qps_query = f'sum(rate(apisix_http_status{{instance="{instance_addr}"}}[5m]))'
        try:
            qps_data = self.prom.query(qps_query)
            if qps_data.get("result"):
                qps_val = float(qps_data["result"][0]["value"][1])
                results.append(self._build_result(
                    "QPS", f"{qps_val:.1f}", "-", "正常"
                ))
        except Exception as e:
            pass

        return results