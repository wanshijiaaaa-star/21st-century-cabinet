"""Start a bundled service without exposing a console window.

This file is copied into the release payload. The native launcher supplies all
paths through environment variables so installed programs stay separate from
the user's databases, cookies, and configuration.
"""

from __future__ import annotations

import os
import runpy
import sys
import traceback
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parent


def _required_path(name: str) -> Path:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"缺少发行版环境变量：{name}")
    return Path(value).resolve()


def _redirect_output(service: str) -> None:
    log_root = _required_path("CENTURY_CABINET_LOG_DIR")
    log_root.mkdir(parents=True, exist_ok=True)
    sys.stdout = (log_root / f"{service}.log").open("a", encoding="utf-8", buffering=1)
    sys.stderr = (log_root / f"{service}-error.log").open("a", encoding="utf-8", buffering=1)


def _write_pid(service: str) -> Path:
    log_root = _required_path("CENTURY_CABINET_LOG_DIR")
    pid_path = log_root / f"{service}.pid"
    pid_path.write_text(str(os.getpid()), encoding="ascii")
    return pid_path


def run_site() -> None:
    site_root = APP_ROOT / "site"
    os.chdir(site_root)
    sys.path.insert(0, str(site_root))
    sys.argv = [str(site_root / "local_server.py"), "--no-browser"]
    runpy.run_path(str(site_root / "local_server.py"), run_name="__main__")


def run_collector() -> None:
    collector_root = APP_ROOT / "we-mp-rss"
    work_root = _required_path("CENTURY_CABINET_COLLECTOR_WORKDIR")
    config_path = _required_path("CENTURY_CABINET_COLLECTOR_CONFIG")
    work_root.mkdir(parents=True, exist_ok=True)
    os.chdir(work_root)
    sys.path.insert(0, str(collector_root))
    sys.argv = [
        str(collector_root / "main.py"),
        "-config",
        str(config_path),
        "-job",
        "True",
        "-init",
        "True",
    ]
    runpy.run_path(str(collector_root / "main.py"), run_name="__main__")


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"site", "collector"}:
        return 2
    service = sys.argv[1]
    _redirect_output(service)
    pid_path = _write_pid(service)
    try:
        if service == "site":
            run_site()
        else:
            run_collector()
        return 0
    except BaseException:
        traceback.print_exc()
        return 1
    finally:
        try:
            pid_path.unlink(missing_ok=True)
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
