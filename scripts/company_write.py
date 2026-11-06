"""Run one company's complete write-and-verify plan under a local file lock."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unicodedata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parent", help="Resolved archive node token or canonical directory")
    parser.add_argument("company", help="Confirmed canonical company name")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not args.command:
        parser.error("缺少写入计划命令")
    try:
        import fcntl
    except ImportError:
        parser.exit(1, "需要使用目标系统等效的进程锁，再开始写入。\n")
    company = "".join(unicodedata.normalize("NFKC", args.company).casefold().split())
    key = hashlib.sha256((args.parent + "\0" + company).encode()).hexdigest()
    directory = Path(tempfile.gettempdir()) / f"interview-review-locks-{os.getuid()}"
    directory.mkdir(mode=0o700, exist_ok=True)
    with (directory / key).open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.exit(1, "同公司已有写入进行中；稍后重新读取再继续。\n")
        # Pass the open lock to the child so an interrupted wrapper cannot unlock it early.
        status = subprocess.run(args.command, pass_fds=(lock.fileno(),)).returncode
        raise SystemExit(status if status >= 0 else 128 - status)


if __name__ == "__main__":
    main()
