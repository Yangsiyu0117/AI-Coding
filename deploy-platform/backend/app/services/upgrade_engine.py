import asyncio
import json
import logging
import os
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.service import Service
from app.models.service_node import ServiceNode
from app.models.task_step import TaskStep
from app.models.upgrade_package import UpgradePackage
from app.models.upgrade_task import UpgradeTask
from app.services.ssh_executor import SSHExecutor
from app.services.crypto import decrypt_password
from app.services.service_types import get_steps, get_rollbackable, get_all_rollbackable

logger = logging.getLogger("deploy_platform")


def _human_error(step_type: str, exit_code: int, stderr: str) -> str:
    """Map common SSH/script errors to human-readable Chinese messages."""
    stderr_lower = stderr.lower()
    if exit_code == 127 or "command not found" in stderr_lower:
        return "命令不存在，请检查 run.sh 是否在部署路径下"
    if "permission denied" in stderr_lower:
        return "权限不足，请检查 SSH 用户是否有执行权限"
    if exit_code == 137:
        return "进程被强制终止，可能是 OOM 内存不足"
    if "no space left" in stderr_lower:
        return "磁盘空间不足，请清理后再试"
    if "connection refused" in stderr_lower:
        return "SSH 连接被拒绝，请检查目标主机端口和服务是否正常"
    if "no such file" in stderr_lower:
        return "文件或目录不存在，请检查部署路径是否正确"
    if "cannot connect" in stderr_lower or "host is down" in stderr_lower:
        return "无法连接到目标主机，请检查网络和主机状态"
    return f"命令执行失败 (exit={exit_code}): {stderr[:200]}"


_task_queues: Dict[int, asyncio.Queue] = {}
_task_controls: Dict[int, dict] = {}


def get_queue(task_id: int) -> asyncio.Queue:
    if task_id not in _task_queues:
        _task_queues[task_id] = asyncio.Queue()
    return _task_queues[task_id]


def _get_control(task_id: int) -> dict:
    if task_id not in _task_controls:
        _task_controls[task_id] = {
            "pause_event": asyncio.Event(),
            "resume_event": asyncio.Event(),
            "stop_event": asyncio.Event(),
        }
    return _task_controls[task_id]


def _cleanup_task(task_id: int):
    _task_queues.pop(task_id, None)
    _task_controls.pop(task_id, None)


def _update_dir(step_type: str) -> str:
    """返回更新包存放目录"""
    date_str = datetime.now().strftime("%Y%m%d")
    suffix = "java" if step_type in ("docker_scp", "docker_load") else "gw"
    from app.services.platform_settings import get as ps_get
    base = ps_get("remote_update_base", settings.remote_update_base)
    return f"{base}/{date_str}_{suffix}"


def _remote_filename(service: Service, pkg: Optional[UpgradePackage] = None) -> str:
    """返回上传到远端更新目录的文件名"""
    if pkg and pkg.file_path:
        return os.path.basename(pkg.file_path)
    return service.name


class UpgradeEngine:

    # ── 步骤类型 ────────────────────────────────────────

    @staticmethod
    def step_types(service_type: str) -> List[str]:
        return get_steps(service_type)

    # ── 控制信号 ────────────────────────────────────────

    def request_pause(self, task_id: int):
        ctrl = _get_control(task_id)
        ctrl["pause_event"].set()

    def request_resume(self, task_id: int):
        ctrl = _get_control(task_id)
        ctrl["pause_event"].clear()
        ctrl["resume_event"].set()

    def request_stop(self, task_id: int):
        ctrl = _get_control(task_id)
        ctrl["stop_event"].set()
        # If paused, also resume so the loop can exit
        if ctrl["pause_event"].is_set():
            ctrl["resume_event"].set()

    # ── 依赖排序 ────────────────────────────────────────

    @staticmethod
    def _resolve_service_order(services: List[Service]) -> List[Service]:
        if len(services) <= 1:
            return services

        name_to_svc = {s.name: s for s in services}
        in_degree: Dict[str, int] = {s.name: 0 for s in services}
        graph: Dict[str, List[str]] = defaultdict(list)

        for svc in services:
            deps = [d.strip() for d in svc.depends_on.split(",") if d.strip()]
            for dep_name in deps:
                if dep_name in name_to_svc:
                    graph[dep_name].append(svc.name)
                    in_degree[svc.name] += 1

        groups: Dict[int, List[Service]] = defaultdict(list)
        q = deque()
        for svc in services:
            if in_degree[svc.name] == 0:
                q.append(svc)

        while q:
            svc = q.popleft()
            groups[svc.upgrade_order].append(svc)
            for downstream in graph.get(svc.name, []):
                in_degree[downstream] -= 1
                if in_degree[downstream] == 0:
                    q.append(name_to_svc[downstream])

        if any(in_degree.values()):
            raise ValueError("Circular dependency detected in depends_on")

        result = []
        for order in sorted(groups):
            result.extend(groups[order])
        return result

    # ── 命令生成 ────────────────────────────────────────

    @staticmethod
    def get_command(step_type: str, service: Service, pkg: Optional[UpgradePackage] = None) -> str:
        dp = service.deploy_path
        name = service.name
        run = service.run_script or "run.sh"
        date_str = datetime.now().strftime("%Y%m%d")

        # ── Go 步骤 ──

        if step_type == "precheck":
            if service.type == "docker":
                return (
                    f"echo ''; echo '=== Precheck: {name} ===' && "
                    f"docker ps | grep {name} && "
                    f"echo 'Precheck done'"
                )
            if service.check_cmd:
                return f"echo ''; echo '=== Precheck: {name} ===' && {service.check_cmd}"
            return (
                f"echo ''; echo '=== Precheck: {name} ===' && "
                f"cd {dp} && sh {run} info 2>/dev/null; sh {run} id 2>/dev/null; "
                f"echo 'Precheck done'"
            )

        if step_type == "backup":
            return (
                f"echo ''; echo '=== Backup: {name} ===' && "
                f"if [ -f {dp}/{name} ]; then "
                f"mv {dp}/{name} {dp}/{name}.{date_str} && echo 'Backup OK: {name}.{date_str}'; "
                f"else echo 'ERROR: Binary not found: {dp}/{name}'; exit 1; fi"
            )

        if step_type == "upload":
            return f"echo ''; echo '=== Upload: {name} ===' && echo 'File will be uploaded to {_update_dir(step_type)}/'"

        if step_type == "copy":
            fname = _remote_filename(service, pkg)
            src = f"{_update_dir('upload')}/{fname}"
            return (
                f"echo ''; echo '=== Copy Update: {name} ===' && "
                f"if [ -f {src} ]; then "
                f"cp {src} {dp}/{name} && chmod +x {dp}/{name} && echo 'Copy OK → {dp}/{name}'; "
                f"else echo 'ERROR: Update file not found: {src}'; exit 1; fi"
            )

        if step_type == "verify":
            bin_path = f"{dp}/{name}"
            lines = [
                f"echo ''; echo '=== Verify: {name} ==='",
                f"if [ -f {bin_path} ]; then ls -la {bin_path} && echo 'File exists OK'; "
                f"else echo 'ERROR: Binary not found: {bin_path}'; exit 1; fi",
            ]
            if pkg and pkg.file_md5:
                lines.append(
                    f"REMOTE_MD5=$(md5sum {bin_path} | awk '{{print $1}}') && "
                    f"if [ \"$REMOTE_MD5\" != \"{pkg.file_md5}\" ]; then "
                    f"echo 'ERROR: MD5 mismatch! Expected: {pkg.file_md5} Got: '$REMOTE_MD5; exit 1; "
                    f"else echo 'MD5 OK: {pkg.file_md5}'; fi"
                )
            return " && ".join(lines)

        if step_type == "verify_version":
            bin_path = f"{dp}/{name}"
            return (
                f"echo ''; echo '=== Version Check: {name} ===' && "
                f"chmod +x {bin_path} && "
                f"({bin_path} -v 2>&1 || {bin_path} --version 2>&1 || echo 'WARN: Could not determine version')"
            )

        if step_type == "stop":
            cmd = service.stop_cmd or f"cd {dp} && sh {run} stop"
            return f"echo ''; echo '=== Stop: {name} ===' && {cmd} && echo 'Stop OK'"

        if step_type == "check_start":
            # Go services auto-restart (via systemd/supervisor), only wait and check
            check = service.check_cmd or f"cd {dp} && sh {run} info 2>/dev/null; sh {run} id 2>/dev/null"
            return (
                f"echo ''; echo '=== Waiting for auto-restart: {name} ===' && "
                f"sleep 5 && "
                f"echo ''; echo '=== Check: {name} ===' && {check}"
            )

        if step_type == "log_check":
            return (
                f"echo ''; echo '=== Log Check: {name} ===' && "
                f"journalctl -u {name} --no-pager -n 20 2>/dev/null || "
                f"find {dp} -name '*.log' -exec echo '--- {{}} ---' \\; -exec tail -20 {{}} \\; 2>/dev/null || "
                f"echo 'No logs found'"
            )

        # ── Docker 步骤 ──

        if step_type == "docker_scp":
            return (
                f"echo ''; echo '=== Docker SCP: {name} ===' && "
                f"echo 'Image file will be uploaded to {_update_dir(step_type)}/'"
            )

        if step_type == "docker_load":
            fname = _remote_filename(service, pkg)
            img_file = f"{_update_dir(step_type)}/{fname}"
            return (
                f"echo ''; echo '=== Docker Load: {name} ===' && "
                f"if [ -f {img_file} ]; then docker load -i {img_file} > /dev/null && echo 'Docker load OK'; "
                f"else echo 'ERROR: Image file not found: {img_file}'; exit 1; fi"
            )

        if step_type == "docker_verify":
            return (
                f"echo ''; echo '=== Docker Verify: {name} ===' && "
                f"if docker images | grep -q {name}; then "
                f"echo 'Image loaded OK'; docker images | grep {name}; "
                f"else echo 'ERROR: Image {name} not found in docker images'; exit 1; fi"
            )

        if step_type == "switch_container":
            new_ver = pkg.version if pkg else "latest"
            detect_old = (
                f"OLD_VER=$(docker inspect --format '{{{{.Config.Image}}}}' {name} 2>/dev/null | "
                f"sed 's/:[^:]*$//' | rev | cut -d/ -f1 | rev | sed 's/^{name}-//') && "
                f"echo 'Old version: '$OLD_VER && "
                f"echo 'New version: {new_ver}' && "
            )
            if service.start_cmd:
                return (
                    f"echo ''; echo '=== Switch Container: {name} ===' && "
                    f"cd {dp} && {service.start_cmd} && "
                    f"echo 'Container started: {name}'"
                )
            return (
                f"echo ''; echo '=== Switch Container: {name} ===' && "
                f"{detect_old}"
                f"cd {dp} && sh {run} $OLD_VER {new_ver} && "
                f"echo 'Container started: {name}'"
            )

        if step_type == "container_check":
            return (
                f"echo ''; echo '=== Container Check: {name} ===' && "
                f"docker ps | grep {name} && "
                f"echo 'Container check done'"
            )

        return f"echo 'Unknown step: {step_type}'"

    # ── 回退命令生成 ────────────────────────────────────

    @staticmethod
    def get_rollback_command(step_type: str, service: Service) -> Optional[str]:
        dp = service.deploy_path
        name = service.name
        date_str = datetime.now().strftime("%Y%m%d")

        if step_type == "backup":
            return (
                f"echo ''; echo '=== Rollback: Restore Backup ({name}) ===' && "
                f"if [ -f {dp}/{name}.{date_str} ]; then "
                f"mv {dp}/{name}.{date_str} {dp}/{name} && echo 'Backup restored: {name}.{date_str} → {name}'; "
                f"else echo 'WARN: No backup file found'; fi"
            )

        if step_type == "upload":
            fname = _remote_filename(service)
            return (
                f"echo ''; echo '=== Rollback: Cleanup Update File ===' && "
                f"rm -f {_update_dir(step_type)}/{fname} && echo 'Update file removed'"
            )

        if step_type == "copy":
            return (
                f"echo ''; echo '=== Rollback: Cleanup Copied Binary ({name}) ===' && "
                f"rm -f {dp}/{name} && echo 'Copied binary removed'"
            )

        if step_type == "docker_scp":
            fname = f"{name}_image.tar.gz"
            return (
                f"echo ''; echo '=== Rollback: Cleanup Image File ===' && "
                f"rm -f {_update_dir(step_type)}/{fname} && echo 'Image file removed'"
            )

        if step_type == "switch_container":
            run = service.run_script or "run.sh"
            if service.start_cmd:
                return (
                    f"echo ''; echo '=== Rollback: Switch Container ({name}) ===' && "
                    f"cd {dp} && {service.start_cmd} && "
                    f"echo 'Rollback container started: {name}'"
                )
            return (
                f"echo ''; echo '=== Rollback: Switch to Latest Container ({name}) ===' && "
                f"cd {dp} && sh {run} latest && "
                f"echo 'Rollback container started: {name}'"
            )

        return None

    # ── 步骤创建 ────────────────────────────────────────

    def create_steps(self, db: Session, task: UpgradeTask,
                      service_ids: List[int], package_ids: List[int]):
        services = db.query(Service).filter(Service.id.in_(service_ids)).all()
        if not services:
            return

        ordered = self._resolve_service_order(services)

        step_order = 0
        for svc in ordered:
            for step_type in self.step_types(svc.type):
                for node in svc.nodes:
                    step_order += 1
                    ts = TaskStep(
                        task_id=task.id,
                        service_id=svc.id,
                        node_id=node.id,
                        step_type=step_type,
                        step_order=step_order,
                        status="pending",
                    )
                    db.add(ts)

        db.commit()

    # ── 任务执行（Wave 并行） ──────────────────────────

    async def run_task(self, task_id: int):
        db = SessionLocal()
        queue = get_queue(task_id)
        ctrl = _get_control(task_id)
        executor = SSHExecutor(default_timeout=settings.ssh_default_timeout)

        try:
            task = db.query(UpgradeTask).filter(UpgradeTask.id == task_id).first()
            if not task or task.status != "pending":
                await queue.put(json.dumps({"type": "task_complete", "status": "skipped"}))
                return

            logger.info(f"Upgrade task {task_id} starting: title={task.title}, strategy={task.failure_strategy}")
            task.started_at = datetime.now(timezone.utc)
            task.status = "running"
            db.commit()

            steps = (
                db.query(TaskStep)
                .filter(TaskStep.task_id == task_id)
                .order_by(TaskStep.step_order)
                .all()
            )

            waves: List[List[TaskStep]] = []
            i = 0
            while i < len(steps):
                wave = [steps[i]]
                j = i + 1
                while j < len(steps) and steps[j].service_id == steps[i].service_id and steps[j].step_type == steps[i].step_type:
                    wave.append(steps[j])
                    j += 1
                waves.append(wave)
                i = j

            step_timeout = task.timeout_seconds or 600

            for wave in waves:
                # Check stop signal
                if ctrl["stop_event"].is_set():
                    await self._handle_stop(task, steps, db, queue)
                    return

                # Check pause signal
                if ctrl["pause_event"].is_set():
                    await self._handle_pause(task, db, queue)
                    ctrl["resume_event"].clear()
                    try:
                        await asyncio.wait_for(ctrl["resume_event"].wait(), timeout=3600)
                    except asyncio.TimeoutError:
                        pass
                    # Re-check stop after resume
                    if ctrl["stop_event"].is_set():
                        await self._handle_stop(task, steps, db, queue)
                        return
                    task.status = "running"
                    db.commit()
                    await queue.put(json.dumps({
                        "type": "task_status", "status": "running",
                    }))

                step_ids = [s.id for s in wave]
                await queue.put(json.dumps({
                    "type": "wave_start", "step_ids": step_ids,
                }))

                for s in wave:
                    s.status = "running"
                    s.started_at = datetime.now(timezone.utc)
                db.commit()

                try:
                    tasks = [self._execute_step(s, db, executor, queue, step_timeout) for s in wave]
                    await asyncio.wait_for(asyncio.gather(*tasks), timeout=step_timeout)
                except asyncio.TimeoutError:
                    for s in wave:
                        if s.status == "running":
                            s.status = "failed"
                            s.error_message = f"Step timed out after {step_timeout}s"
                            s.log_output = (s.log_output or "") + f"\n[TIMEOUT] Step exceeded {step_timeout}s limit\n"
                    db.commit()

                for s in wave:
                    s.finished_at = datetime.now(timezone.utc)
                db.commit()

                for s in wave:
                    await queue.put(json.dumps({
                        "type": "step_update", "step_id": s.id, "status": s.status,
                    }))

                if any(s.status == "failed" for s in wave):
                    # Check if stopped
                    if ctrl["stop_event"].is_set():
                        await self._handle_stop(task, steps, db, queue)
                        return
                    strategy = task.failure_strategy or "stop"
                    if strategy == "rollback":
                        await self.rollback_task(task_id)
                        return
                    elif strategy == "continue":
                        continue
                    else:
                        break

            all_success = all(s.status == "success" for s in steps)
            task.status = "success" if all_success else "failed"
            task.finished_at = datetime.now(timezone.utc)
            db.commit()

            logger.info(
                f"Upgrade task {task_id} completed: status={task.status}, "
                f"success_steps={sum(1 for s in steps if s.status == 'success')}, "
                f"failed_steps={sum(1 for s in steps if s.status == 'failed')}"
            )

            await queue.put(json.dumps({
                "type": "task_complete", "status": task.status,
            }))
        except Exception as e:
            logger.exception(f"Upgrade task {task_id} failed with unhandled exception")
            try:
                task.status = "failed"
                task.finished_at = datetime.now(timezone.utc)
                for s in steps:
                    if s.status == "running":
                        s.status = "failed"
                        s.error_message = (s.error_message or "") + f"\nUnhandled error: {e}"
                        s.finished_at = datetime.now(timezone.utc)
                db.commit()
            except Exception:
                pass
            await queue.put(json.dumps({
                "type": "task_complete", "status": "error", "message": str(e),
            }))
        finally:
            db.close()
            await queue.put(None)
            _cleanup_task(task_id)

    async def _execute_step(self, step: TaskStep, db: Session,
                              executor: SSHExecutor, queue: asyncio.Queue,
                              timeout: int = 300):
        node = db.query(ServiceNode).filter(ServiceNode.id == step.node_id).first()
        service = db.query(Service).filter(Service.id == step.service_id).first()
        if not node or not service:
            step.status = "failed"
            step.error_message = "Node or service not found"
            return

        pkg = (
            db.query(UpgradePackage)
            .filter(UpgradePackage.service_id == service.id)
            .order_by(UpgradePackage.created_at.desc())
            .first()
        )

        if step.step_type in ("upload", "docker_scp"):
            await self._run_upload_step(step, node, service, pkg, executor, queue, db, timeout)
        else:
            command = self.get_command(step.step_type, service, pkg)
            await self._run_command_step(step, node, command, executor, queue, db, timeout)

    # ── 暂停/停止处理 ────────────────────────────────────

    async def _handle_pause(self, task: UpgradeTask, db: Session, queue: asyncio.Queue):
        task.status = "paused"
        db.commit()
        await queue.put(json.dumps({
            "type": "task_status", "status": "paused",
        }))

    async def _handle_stop(self, task: UpgradeTask, steps: list, db: Session, queue: asyncio.Queue):
        task.status = "failed"
        task.finished_at = datetime.now(timezone.utc)
        # Mark any still-running steps as failed
        for s in steps:
            if s.status == "running":
                s.status = "failed"
                s.error_message = (s.error_message or "") + "\nTask stopped by user"
                s.finished_at = datetime.now(timezone.utc)
            elif s.status == "pending":
                s.status = "failed"
                s.error_message = "Task stopped by user"
        db.commit()
        await queue.put(json.dumps({
            "type": "task_status", "status": "failed",
            "message": "Task stopped by user",
        }))
        await queue.put(json.dumps({
            "type": "task_complete", "status": "failed",
        }))

    # ── 回退 ────────────────────────────────────────────

    async def rollback_task(self, task_id: int):
        db = SessionLocal()
        queue = get_queue(task_id)
        executor = SSHExecutor(default_timeout=settings.ssh_default_timeout)

        try:
            task = db.query(UpgradeTask).filter(UpgradeTask.id == task_id).first()
            if not task:
                return

            logger.info(f"Rollback task {task_id} starting")
            task.rollback_status = "rolling_back"
            db.commit()

            await queue.put(json.dumps({
                "type": "rollback_start", "task_id": task_id,
            }))

            steps = (
                db.query(TaskStep)
                .filter(TaskStep.task_id == task_id, TaskStep.status == "success")
                .filter(TaskStep.step_type.in_(get_all_rollbackable()))
                .order_by(TaskStep.step_order.desc())
                .all()
            )

            failed = False
            for step in steps:
                logger.info(
                    f"Rollback step {step.id}: {step.step_type} on node {step.node_id}"
                )
                step.rollback_status = "rolling_back"
                db.commit()

                await queue.put(json.dumps({
                    "type": "step_update", "step_id": step.id,
                    "rollback_status": "rolling_back",
                }))

                node = db.query(ServiceNode).filter(ServiceNode.id == step.node_id).first()
                service = db.query(Service).filter(Service.id == step.service_id).first()
                if not node or not service:
                    step.rollback_status = "rollback_failed"
                    step.error_message = (step.error_message or "") + "\nRollback: Node or service not found"
                    failed = True
                    db.commit()
                    continue

                cmd = self.get_rollback_command(step.step_type, service)
                if cmd is None:
                    step.rollback_status = "rollback_skipped"
                    db.commit()
                    continue

                await queue.put(json.dumps({
                    "type": "log", "step_id": step.id,
                    "text": f"\n=== ROLLBACK ===\n$ {cmd}\n",
                }))

                result = await executor.execute(
                    host=node.host_ip,
                    command=cmd,
                    port=node.ssh_port,
                    user=node.ssh_user,
                    password=decrypt_password(node.ssh_password) or "",
                )

                rollback_log = "\n=== ROLLBACK ===\n" + cmd + "\n"
                if result.stdout:
                    rollback_log += result.stdout
                if result.stderr:
                    rollback_log += result.stderr

                step.log_output = (step.log_output or "") + rollback_log

                if result.success:
                    step.rollback_status = "rollback_success"
                    logger.info(f"Rollback step {step.id} succeeded")
                else:
                    step.rollback_status = "rollback_failed"
                    step.error_message = (step.error_message or "") + f"\nRollback failed: exit code {result.exit_code}"
                    failed = True
                    logger.error(
                        f"Rollback step {step.id} failed: step_type={step.step_type}, "
                        f"exit_code={result.exit_code}"
                    )

                db.commit()

                await queue.put(json.dumps({
                    "type": "log", "step_id": step.id, "text": rollback_log,
                }))
                await queue.put(json.dumps({
                    "type": "step_update", "step_id": step.id,
                    "rollback_status": step.rollback_status,
                }))

            task.rollback_status = "rollback_failed" if failed else "rollback_complete"
            db.commit()

            logger.info(f"Rollback task {task_id} completed: status={task.rollback_status}")

            await queue.put(json.dumps({
                "type": "rollback_complete", "task_id": task_id,
                "status": task.rollback_status,
            }))
        except Exception as e:
            logger.exception(f"Rollback task {task_id} failed with unhandled exception")
            await queue.put(json.dumps({
                "type": "rollback_complete", "task_id": task_id,
                "status": "error", "message": str(e),
            }))
        finally:
            db.close()
            await queue.put(None)

    # ── 步骤重试 ────────────────────────────────────────

    async def retry_step(self, task_id: int, step_id: int):
        db = SessionLocal()
        queue = get_queue(task_id)
        executor = SSHExecutor(default_timeout=settings.ssh_default_timeout)

        try:
            step = db.query(TaskStep).filter(TaskStep.id == step_id, TaskStep.task_id == task_id).first()
            if not step:
                await queue.put(json.dumps({"type": "step_update", "step_id": step_id, "status": "failed"}))
                return

            task = db.query(UpgradeTask).filter(UpgradeTask.id == task_id).first()
            node = db.query(ServiceNode).filter(ServiceNode.id == step.node_id).first()
            service = db.query(Service).filter(Service.id == step.service_id).first()

            if not node or not service:
                step.status = "failed"
                step.error_message = "Node or service not found"
                db.commit()
                await queue.put(json.dumps({"type": "step_update", "step_id": step_id, "status": "failed"}))
                return

            step.status = "running"
            step.started_at = datetime.now(timezone.utc)
            db.commit()

            await queue.put(json.dumps({
                "type": "step_update", "step_id": step_id, "status": "running",
            }))

            step_timeout = task.timeout_seconds or 600 if task else 600
            await self._execute_step(step, db, executor, queue, step_timeout)

            step.finished_at = datetime.now(timezone.utc)
            db.commit()

            await queue.put(json.dumps({
                "type": "step_update", "step_id": step_id, "status": step.status,
            }))

            # After retry, check overall task status
            if task:
                all_steps = (
                    db.query(TaskStep)
                    .filter(TaskStep.task_id == task_id)
                    .all()
                )
                statuses = {s.status for s in all_steps}
                if statuses == {"success"}:
                    task.status = "success"
                    task.finished_at = datetime.now(timezone.utc)
                elif "running" in statuses or "pending" in statuses:
                    task.status = "running"
                else:
                    # Some steps still failed — leave task as failed
                    task.status = "failed"
                db.commit()

                if task.status == "success":
                    await queue.put(json.dumps({
                        "type": "task_complete", "status": "success",
                    }))

            logger.info(
                f"Retry step {step_id} of task {task_id} completed: status={step.status}"
            )

        except Exception as e:
            logger.exception(f"Retry step {step_id} of task {task_id} failed with unhandled exception")
            try:
                step = db.query(TaskStep).filter(TaskStep.id == step_id).first()
                if step and step.status == "running":
                    step.status = "failed"
                    step.error_message = (step.error_message or "") + f"\nUnhandled error: {e}"
                    step.finished_at = datetime.now(timezone.utc)
                    db.commit()
                await queue.put(json.dumps({
                    "type": "step_update", "step_id": step_id, "status": "failed",
                }))
            except Exception:
                pass
        finally:
            db.close()

    # ── 内部辅助 ────────────────────────────────────────

    async def _run_command_step(self, step: TaskStep, node: ServiceNode,
                                  command: str, executor: SSHExecutor,
                                  queue: asyncio.Queue, db: Session,
                                  timeout: int = 300):
        logger.info(
            f"Step {step.id}: {step.step_type} on {node.host_ip} "
            f"(service_id={step.service_id}, timeout={timeout}s)"
        )
        sep = "=" * 60
        cmd_header = f"\n{sep}\n  {step.step_type} @ {node.host_ip}\n{sep}\n$ {command}\n"

        # Append header to existing log so previous retry attempts are preserved
        step.log_output = (step.log_output or "") + cmd_header
        db.commit()

        await queue.put(json.dumps({
            "type": "log", "step_id": step.id, "text": cmd_header,
        }))

        result = await executor.execute(
            host=node.host_ip,
            command=command,
            port=node.ssh_port,
            user=node.ssh_user,
            password=decrypt_password(node.ssh_password) or "",
            timeout=timeout,
        )

        # Send only the new output as delta (header was already sent above)
        delta_parts = []
        if result.stdout:
            delta_parts.append(result.stdout)
        if result.stderr:
            delta_parts.append(result.stderr)

        delta = "".join(delta_parts)
        step.log_output = (step.log_output or "") + delta
        db.commit()

        if delta:
            await queue.put(json.dumps({
                "type": "log", "step_id": step.id, "text": delta,
            }))

        if result.success:
            step.status = "success"
            logger.info(f"Step {step.id} succeeded: exit_code={result.exit_code}")
        else:
            step.status = "failed"
            step.error_message = _human_error(step.step_type, result.exit_code, result.stderr)
            logger.error(
                f"Step {step.id} failed: step_type={step.step_type}, "
                f"host={node.host_ip}, exit_code={result.exit_code}, "
                f"error={step.error_message[:200]}"
            )

    async def _run_upload_step(self, step: TaskStep, node: ServiceNode,
                                 service: Service, pkg: Optional[UpgradePackage],
                                 executor: SSHExecutor, queue: asyncio.Queue,
                                 db: Session, timeout: int = 300):
        if not pkg:
            logger.error(f"Step {step.id}: No package found for service {service.name}")
            await queue.put(json.dumps({
                "type": "log", "step_id": step.id,
                "text": "ERROR: No package found for this service\n",
            }))
            step.status = "failed"
            step.error_message = "No package found for this service"
            return

        local_file = pkg.file_path
        remote_dir = _update_dir(step.step_type)
        remote_file = f"{remote_dir}/{_remote_filename(service, pkg)}"

        file_size_mb = round(os.path.getsize(local_file) / (1024 * 1024), 1) if os.path.exists(local_file) else 0
        logger.info(
            f"Step {step.id}: upload to {node.host_ip}, "
            f"file={os.path.basename(local_file)}, size={file_size_mb}MB, dest={remote_file}"
        )

        sep = "=" * 60
        msg = (
            f"\n{sep}\n  {step.step_type} @ {node.host_ip}\n{sep}\n"
            f"Uploading {local_file} → {node.host_ip}:{remote_file}\n"
        )

        # Save initial log before slow upload so page refresh shows progress
        step.log_output = msg
        db.commit()

        # Create remote directory first
        mkdir_result = await executor.execute(
            host=node.host_ip,
            command=f"mkdir -p {remote_dir} && echo 'Dir OK: {remote_dir}'",
            port=node.ssh_port,
            user=node.ssh_user,
            password=decrypt_password(node.ssh_password) or "",
        )
        if mkdir_result.stdout:
            msg += mkdir_result.stdout + "\n"

        await queue.put(json.dumps({
            "type": "log", "step_id": step.id, "text": msg,
        }))

        ok = await executor.upload_file(
            host=node.host_ip,
            local_path=local_file,
            remote_path=remote_file,
            port=node.ssh_port,
            user=node.ssh_user,
            password=decrypt_password(node.ssh_password) or "",
            timeout=timeout,
        )

        if ok:
            step.status = "success"
            step.log_output = msg + "Upload completed\n"
            logger.info(f"Step {step.id}: upload succeeded to {node.host_ip}")
        else:
            step.status = "failed"
            step.error_message = _human_error(step.step_type, -1, "SFTP upload failed")
            step.log_output = msg + "Upload FAILED\n"
            logger.error(
                f"Step {step.id}: upload failed to {node.host_ip}, "
                f"file={os.path.basename(local_file)}"
            )

        await queue.put(json.dumps({
            "type": "log", "step_id": step.id, "text": step.log_output,
        }))
