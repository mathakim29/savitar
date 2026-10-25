import subprocess
import sys
from pathlib import Path

from .app import BUILD_JS, OUT, build_env, ensure_svelte, find_bun


def main():
    """Build the frontend or manage packages in uv's active environment."""
    args = sys.argv[1:]
    if args and args[0] == "pkg":
        pkg_args = args[1:]
        if not pkg_args:
            sys.exit("usage: savitar pkg <add|remove|...> [packages]")

        bun = find_bun()
        subprocess.run([bun, *pkg_args, "--cwd", str(Path(sys.prefix))], check=True)
        return

    if args and args[0] == "build":
        args = args[1:]
    web = Path(args[0] if args else "web").resolve()
    if not (web / "App.svelte").exists():
        sys.exit(f"savitar: {web / 'App.svelte'} not found")

    bun = find_bun()
    ensure_svelte(bun)
    OUT.mkdir(parents=True, exist_ok=True)
    subprocess.run([bun, str(BUILD_JS)], check=True, env=build_env(web))
