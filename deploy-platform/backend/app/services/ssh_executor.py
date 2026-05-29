import asyncio
import logging
import socket
import time
from dataclasses import dataclass

import paramiko

logger = logging.getLogger("deploy_platform")


@dataclass
class SSHResult:
    host: str
    command: str
    stdout: str
    stderr: str
    exit_code: int
    success: bool


@dataclass
class SSHTestResult:
    success: bool
    message: str
    latency_ms: int = 0


class SSHExecutor:
    """SSH 远程执行器"""

    def __init__(self, default_timeout: int = 10):
        self._default_timeout = default_timeout

    def _ssh_exec(self, host: str, command: str, port: int, user: str,
                   password: str, timeout: int) -> SSHResult:
        """同步 SSH 执行，在线程池中运行"""
        logger.debug(f"SSH exec on {host}: {command[:200]}")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(
                hostname=host,
                port=port,
                username=user,
                password=password,
                timeout=min(timeout, 30),
                allow_agent=False,
                look_for_keys=False,
            )
            stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
            # Set channel timeout so read() doesn't block forever
            stdout.channel.settimeout(timeout)
            stderr.channel.settimeout(timeout)
            out_str = stdout.read().decode("utf-8", errors="replace")
            err_str = stderr.read().decode("utf-8", errors="replace")
            exit_code = stdout.channel.recv_exit_status()
            result = SSHResult(
                host=host,
                command=command,
                stdout=out_str,
                stderr=err_str,
                exit_code=exit_code,
                success=exit_code == 0,
            )
            if not result.success:
                logger.error(
                    f"SSH command failed on {host}: exit_code={exit_code}, "
                    f"stderr={err_str[:200]}"
                )
            return result
        finally:
            ssh.close()

    def _sftp_upload(self, host: str, local_path: str, remote_path: str,
                      port: int, user: str, password: str,
                      timeout: int = 300) -> bool:
        """同步 SFTP 上传，在线程池中运行"""
        logger.debug(f"SFTP upload: {local_path} → {host}:{remote_path}")
        transport = None
        try:
            transport = paramiko.Transport((host, port))
            transport.banner_timeout = timeout
            transport.connect(username=user, password=password)
            transport.sock.settimeout(timeout)
            sftp = paramiko.SFTPClient.from_transport(transport)
            sftp.put(local_path, remote_path)
            return True
        except Exception:
            logger.exception(f"SFTP upload failed: {local_path} → {host}:{remote_path}")
            return False
        finally:
            if transport:
                transport.close()

    async def execute(self, host: str, command: str, port: int = 22,
                       user: str = "root", password: str = "",
                       timeout: int = 30) -> SSHResult:
        return await asyncio.to_thread(
            self._ssh_exec, host, command, port, user, password, timeout,
        )

    async def upload_file(self, host: str, local_path: str, remote_path: str,
                           port: int = 22, user: str = "root",
                           password: str = "", timeout: int = 300) -> bool:
        return await asyncio.to_thread(
            self._sftp_upload, host, local_path, remote_path, port, user, password, timeout,
        )

    async def test_connection(
        self, host: str, port: int, user: str,
        password: str | None = None, timeout: int = 5,
    ) -> SSHTestResult:
        tcp_start = time.monotonic()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        try:
            sock.connect((host, port))
        except socket.timeout:
            return SSHTestResult(success=False, message=f"TCP connection to {host}:{port} timed out")
        except ConnectionRefusedError:
            return SSHTestResult(success=False, message=f"Connection refused: {host}:{port}")
        except socket.gaierror as e:
            logger.warning(f"Host resolution failed: {host}: {e}")
            return SSHTestResult(success=False, message=f"Host resolution failed: {e}")
        except OSError as e:
            logger.warning(f"Connection failed: {host}:{port} — {e}")
            return SSHTestResult(success=False, message=f"Connection failed: {e}")
        finally:
            sock.close()

        tcp_latency = int((time.monotonic() - tcp_start) * 1000)

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(
                hostname=host,
                port=port,
                username=user,
                password=password,
                timeout=min(timeout, self._default_timeout),
                allow_agent=False,
                look_for_keys=False,
            )
            ssh.close()
            return SSHTestResult(success=True, message="SSH connection successful", latency_ms=tcp_latency)
        except paramiko.AuthenticationException:
            return SSHTestResult(success=False, message=f"Authentication failed for user '{user}'", latency_ms=tcp_latency)
        except paramiko.SSHException as e:
            return SSHTestResult(success=False, message=f"SSH error: {e}", latency_ms=tcp_latency)
        except socket.timeout:
            return SSHTestResult(success=False, message=f"SSH connection to {host}:{port} timed out", latency_ms=tcp_latency)
        except OSError as e:
            return SSHTestResult(success=False, message=f"Connection error: {e}", latency_ms=tcp_latency)

    async def execute_batch(self, hosts: list[str], command: str, port: int = 22,
                             user: str = "root", password: str = "",
                             timeout: int = 30) -> list[SSHResult]:
        tasks = [
            self.execute(host, command, port, user, password, timeout)
            for host in hosts
        ]
        return await asyncio.gather(*tasks)
