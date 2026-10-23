"""
本机一键启动：API + ARQ Worker + 前端 Vite。

用法（在项目根目录）：
  python run.py

依赖：已配置 .env（数据库 / Redis），本机可访问；前端已 npm install。
按 Ctrl+C 结束全部子进程。
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
API_PORT = os.environ.get("API_PORT", "7302")
FE_PORT = os.environ.get("FE_PORT", "7301")


class LocalStackLauncher:
    """管理本机开发用的前后端子进程。"""

    def __init__(self) -> None:
        self._processes: list[subprocess.Popen[str]] = []
        self._python = sys.executable

    def start(self) -> None:
        self._ensure_layout()
        print(f"[run] Python: {self._python}")
        print(f"[run] 项目根: {ROOT}")
        print("[run] 启动 API / Worker / 前端 …\n")

        self._spawn(
            "api",
            [
                self._python,
                "-m",
                "uvicorn",
                "app.main:app",
                "--reload",
                "--host",
                "0.0.0.0",
                "--port",
                API_PORT,
            ],
            cwd=BACKEND,
        )
        self._spawn(
            "worker",
            [self._python, "-m", "arq", "app.worker.WorkerSettings"],
            cwd=BACKEND,
        )
        self._spawn(
            "frontend",
            self._frontend_command(),
            cwd=FRONTEND,
            shell=sys.platform == "win32",
        )

        print(
            f"\n[run] 就绪后打开: http://127.0.0.1:{FE_PORT}/\n"
            f"[run] API 文档: http://127.0.0.1:{API_PORT}/api/docs\n"
            "[run] 按 Ctrl+C 停止全部服务\n"
        )
        self._wait_until_interrupted()

    def _ensure_layout(self) -> None:
        if not (BACKEND / "app" / "main.py").is_file():
            raise SystemExit(f"未找到后端: {BACKEND / 'app' / 'main.py'}")
        if not (FRONTEND / "package.json").is_file():
            raise SystemExit(f"未找到前端: {FRONTEND / 'package.json'}")
        if not (FRONTEND / "node_modules").is_dir():
            raise SystemExit(
                "前端依赖未安装。请先执行:\n"
                f"  cd {FRONTEND}\n"
                "  npm install"
            )

    def _frontend_command(self) -> list[str]:
        # Windows 上 npm 常为 .cmd，用 shell 启动更稳
        if sys.platform == "win32":
            return [
                "npm",
                "run",
                "dev",
                "--",
                "--host",
                "127.0.0.1",
                "--port",
                FE_PORT,
            ]
        return [
            "npm",
            "run",
            "dev",
            "--",
            "--host",
            "127.0.0.1",
            "--port",
            FE_PORT,
        ]

    def _spawn(
        self,
        name: str,
        command: list[str],
        *,
        cwd: Path,
        shell: bool = False,
    ) -> None:
        env = os.environ.copy()
        # 保证能 import app.*
        pythonpath = env.get("PYTHONPATH", "")
        backend_str = str(BACKEND)
        env["PYTHONPATH"] = (
            backend_str
            if not pythonpath
            else f"{backend_str}{os.pathsep}{pythonpath}"
        )

        print(f"[run] + {name}: {' '.join(command)}  (cwd={cwd})")
        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            env=env,
            shell=shell,
        )
        self._processes.append(process)

    def _wait_until_interrupted(self) -> None:
        try:
            while True:
                # 任一关键进程意外退出则结束整栈，避免假活着
                for process in self._processes:
                    code = process.poll()
                    if code is not None:
                        print(
                            f"\n[run] 子进程退出 (pid={process.pid}, code={code})，准备关闭其余服务…"
                        )
                        self.stop()
                        raise SystemExit(code if code else 1)
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n[run] 收到 Ctrl+C，正在关闭…")
            self.stop()

    def stop(self) -> None:
        for process in reversed(self._processes):
            if process.poll() is not None:
                continue
            try:
                if sys.platform == "win32":
                    # 结束进程树，避免 --reload 留下子进程
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                        capture_output=True,
                        check=False,
                    )
                else:
                    process.send_signal(signal.SIGTERM)
                    try:
                        process.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        process.kill()
            except OSError:
                pass
        self._processes.clear()
        print("[run] 已停止。")


def main() -> None:
    launcher = LocalStackLauncher()
    launcher.start()


if __name__ == "__main__":
    main()
