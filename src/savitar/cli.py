import subprocess
import sys
from pathlib import Path

from . import config
from .app import BUILD_JS, VENV, build_env, check_venv, ensure_deps, find_bun, out_dir

ADD = {"add", "a", "install", "i"}
REMOVE = {"remove", "rm", "r"}


def pkg(args):
    """savitar pkg <add|remove|...> [packages]  -> bun in uv's venv, recorded in pyproject"""
    if not args:
        sys.exit("usage: savitar pkg <add|remove|...> [packages]")
    check_venv()
    cmd, rest = args[0], args[1:]
    subprocess.run([find_bun(), *args, "--cwd", str(VENV)], check=True)

    names = [a for a in rest if not a.startswith("-")]
    if cmd in ADD and names:
        config.add_packages(names)
    elif cmd in REMOVE and names:
        config.remove_packages(names)


def exec_bun(args):
    """savitar exec <bun args>  -> run Bun with the active venv as --cwd."""
    if not args:
        sys.exit("usage: savitar exec <bun command> [args]")
    check_venv()
    return subprocess.run([find_bun(), "--cwd", str(VENV), *args]).returncode


def build(args):
    """savitar build [web_folder]  -> one-shot build (run before starting workers)"""
    cfg, root = config.load()
    web = Path(args[0]).resolve() if args else (root / cfg.get("web", "web")).resolve()
    if not (web / "App.svelte").exists():
        sys.exit(f"savitar: {web / 'App.svelte'} not found")

    bun = find_bun()
    ensure_deps(bun, cfg.get("packages", []))
    out = out_dir(web)
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run([bun, str(BUILD_JS)], check=True, env=build_env(web, out))


def main():
    args = sys.argv[1:]
    if args and args[0] == "pkg":
        return pkg(args[1:])
    if args and args[0] == "exec":
        return exec_bun(args[1:])
    if args and args[0] == "build":
        args = args[1:]
    return build(args)
