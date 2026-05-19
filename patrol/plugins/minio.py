"""MinIO plugin"""
from plugins.base import BasePlugin


class MinioPlugin(BasePlugin):
    """MinIO对象存储巡检插件"""

    def inspect(self, instance) -> list:
        results = []
        instance_addr = instance["instance"]

        # Disk Usage
        disk_query = f'sum(minio_bucket_usage_object_total{{instance="{instance_addr}"}}) by (bucket)'
        try:
            disk_data = self.prom.query(disk_query)
            for r in disk_data.get("result", []):
                bucket = r["metric"].get("bucket", "unknown")
                obj_count = float(r["value"][1])
                results.append(self._build_result(
                    f"对象数({bucket})", f"{obj_count:.0f}", "-", "正常"
                ))
        except Exception as e:
            results.append(self._build_result("对象数", str(e), "-", "严重", "查询失败"))

        # Disk offline
        offline_query = f'minio_disk_offline{{instance="{instance_addr}"}}'
        try:
            offline_data = self.prom.query(offline_query)
            for r in offline_data.get("result", []):
                offline = int(r["value"][1])
                disk = r["metric"].get("disk", "unknown")
                status = "严重" if offline > 0 else "正常"
                results.append(self._build_result(
                    f"磁盘状态({disk})", "离线" if offline else "在线", "在线", status
                ))
        except Exception as e:
            pass

        return results