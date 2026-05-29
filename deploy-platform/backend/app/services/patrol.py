import asyncio
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.service import Service
from app.models.service_node import ServiceNode
from app.services.ssh_executor import SSHExecutor


class PatrolService:
    """状态巡检服务"""

    def __init__(self, default_timeout: int = 10):
        self._executor = SSHExecutor(default_timeout=default_timeout)

    async def check_node(self, node: ServiceNode, service: Service) -> dict:
        """检查单个节点上服务状态，返回 {healthy: bool, detail: str}"""
        if service.type == "docker":
            cmd = f"docker ps --filter name={service.name} --format '{{{{.Status}}}}' 2>&1"
        elif service.check_cmd:
            cmd = service.check_cmd
        elif service.version_cmd:
            cmd = service.version_cmd
        else:
            cmd = f"ps aux | grep -v grep | grep {service.name} || echo 'Process not found'"

        result = await self._executor.execute(
            host=node.host_ip,
            command=cmd,
            port=node.ssh_port,
            user=node.ssh_user,
            password=node.ssh_password or "",
            timeout=10,
        )

        if result.success:
            detail = (result.stdout or "").strip()[:500]
            if not detail:
                detail = "OK (no output)"
            return {"healthy": True, "detail": detail}
        else:
            error = (result.stderr or result.stdout or f"exit code {result.exit_code}").strip()
            return {"healthy": False, "detail": error[:500]}

    async def run_patrol(
        self, db: Session, environment_id: int, service_ids: list[int] | None = None,
    ) -> dict:
        """执行完整巡检，返回 {environment_id, total, healthy, unhealthy, results, checked_at}"""
        q = (
            db.query(Service)
            .filter(Service.environment_id == environment_id)
        )
        if service_ids:
            q = q.filter(Service.id.in_(service_ids))

        services = q.all()

        tasks = []
        task_meta: list[tuple[ServiceNode, Service]] = []
        for svc in services:
            for node in svc.nodes:
                tasks.append(self.check_node(node, svc))
                task_meta.append((node, svc))

        results_raw = await asyncio.gather(*tasks)

        results = []
        for (node, svc), r in zip(task_meta, results_raw):
            results.append({
                "node_id": node.id,
                "host_ip": node.host_ip,
                "service_name": svc.name,
                "status": "healthy" if r["healthy"] else "unhealthy",
                "detail": r["detail"],
                "checked_at": datetime.now(timezone.utc),
            })

        healthy = sum(1 for r in results if r["status"] == "healthy")
        unhealthy = len(results) - healthy

        return {
            "environment_id": environment_id,
            "total_nodes": len(results),
            "healthy_nodes": healthy,
            "unhealthy_nodes": unhealthy,
            "results": results,
            "checked_at": datetime.now(timezone.utc),
        }
