"""ARQ Worker 入口：python -m app.worker"""

from arq.connections import RedisSettings

from app.config import get_settings
from app.tasks.agent import execute_agent_plan
from app.tasks.tools import execute_tool_run


class WorkerSettings:
    """arq 读取此类作为 Worker 配置。"""

    functions = [execute_tool_run, execute_agent_plan]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 5
    # Agent 串行多步，放宽超时
    job_timeout = 600



def run() -> None:
    """启动 Worker 进程。"""
    from arq.worker import run_worker

    run_worker(WorkerSettings)



if __name__ == "__main__":
    run()
