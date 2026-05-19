"""Base plugin interface"""
from abc import ABC, abstractmethod


class BasePlugin(ABC):
    """所有巡检插件的基类"""

    def __init__(self, prometheus_client=None, thresholds=None, extra_config=None, datasource=None):
        if datasource is not None:
            self.datasource = datasource
            self.prom = getattr(datasource, '_client', None) or datasource
        else:
            self.datasource = None
            self.prom = prometheus_client
        self.thresholds = thresholds or {}
        self.extra_config = extra_config or {}

    @abstractmethod
    def inspect(self, instance) -> list:
        """
        对单个实例执行巡检
        返回: [{"metric_name": str, "current_value": any, "threshold_value": str, "status": "正常"|"警告"|"严重", "detail": str}]
        """
        pass

    def _check_threshold(self, metric_name, value, warning_val=None, critical_val=None):
        """Check if a value exceeds thresholds"""
        warning_val = warning_val or self.thresholds.get(f"{metric_name}_warning")
        critical_val = critical_val or self.thresholds.get(f"{metric_name}")

        if critical_val is not None and value >= float(critical_val):
            return "严重"
        if warning_val is not None and value >= float(warning_val):
            return "警告"
        return "正常"

    def _build_result(self, metric_name, current_value, threshold_str, status, detail=""):
        return {
            "metric_name": metric_name,
            "current_value": current_value,
            "threshold_value": threshold_str,
            "status": status,
            "detail": detail
        }