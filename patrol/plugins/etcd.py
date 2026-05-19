"""etcd plugin"""
from plugins.base import BasePlugin


class EtcdPlugin(BasePlugin):
    """etcd集群巡检插件"""

    def inspect(self, instance) -> list:
        results = []
        instance_addr = instance["instance"]

        # Is Leader
        leader_query = f'etcd_server_is_leader{{instance="{instance_addr}"}}'
        try:
            leader_data = self.prom.query(leader_query)
            if leader_data.get("result"):
                is_leader = int(leader_data["result"][0]["value"][1])
                results.append(self._build_result(
                    "Leader状态", "是" if is_leader else "否", "-", "正常"
                ))
        except Exception as e:
            results.append(self._build_result("Leader状态", str(e), "-", "严重", "查询失败"))

        # Has Leader
        has_leader_query = f'etcd_server_has_leader{{instance="{instance_addr}"}}'
        try:
            has_leader_data = self.prom.query(has_leader_query)
            if has_leader_data.get("result"):
                has_leader = int(has_leader_data["result"][0]["value"][1])
                status = "正常" if has_leader else "严重"
                results.append(self._build_result(
                    "集群Leader存在", "是" if has_leader else "否",
                    "是", status
                ))
        except Exception as e:
            results.append(self._build_result("集群Leader", str(e), "-", "严重", "查询失败"))

        # Proposals pending
        pending_query = f'etcd_server_proposals_pending{{instance="{instance_addr}"}}'
        try:
            pending_data = self.prom.query(pending_query)
            if pending_data.get("result"):
                pending_val = float(pending_data["result"][0]["value"][1])
                status = "正常" if pending_val == 0 else "警告"
                results.append(self._build_result(
                    "待处理提案数", f"{pending_val:.0f}", "0", status
                ))
        except Exception as e:
            pass

        return results