import asyncio
import hashlib
import os
import shutil
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from . import config

BUILD_JS = Path(__file__).parent / "build.js"
VENV = Path(sys.prefix)  # whatever venv uv is using


def check_venv() -> None:
    if sys.prefix == sys.base_prefix:
        raise RuntimeError("savitar: no virtualenv active (run with `uv run`)")


def out_dir(web: Path) -> Path:
    """Build output, one per frontend folder (generated, don't edit)."""
    key = hashlib.sha1(str(web).encode()).hexdigest()[:8]
    return VENV / "savitar" / key / "web"


def find_bun() -> str:
    """bun from bun-wheel lives in <venv>/bin; fall back to PATH."""
    for sub in ("bin", "Scripts"):
        for name in ("bun", "bun.exe"):
            p = VENV / sub / name
            if p.exists():
                return str(p)
    found = shutil.which("bun")
    if not found:
        raise RuntimeError("savitar: bun not found (expected from bun-wheel)")
    return found


def ensure_deps(bun: str, packages=()) -> None:
    """svelte + [tool.savitar] packages live in <venv>/node_modules."""
    check_venv()
    nm = VENV / "node_modules"
    packages = list(packages)
    names = {config.pkg_name(p) for p in packages}
    missing = []
    if "svelte" not in names and not (nm / "svelte" / "package.json").exists():
        missing.append("svelte")
    missing += [p for p in packages if not (nm / config.pkg_name(p) / "package.json").exists()]
    if missing:
        subprocess.run([bun, "add", *missing, "--cwd", str(VENV)], check=True)


def build_env(web: Path, out: Path) -> dict:
    return {
        **os.environ,
        "VIRTUAL_ENV": str(VENV),
        "SAVITAR_SRC": str(web),
        "SAVITAR_OUT": str(out),
    }


class _Static(StaticFiles):
    """StaticFiles + SPA fallback (unknown non-file, non-api paths -> index.html)."""

    def __init__(self, *, api_prefix, spa, **kw):
        super().__init__(**kw)
        self._api = api_prefix.strip("/")
        self._spa = spa

    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as e:
            is_api = bool(self._api) and (path == self._api or path.startswith(self._api + "/"))
            is_file = "." in path.rsplit("/", 1)[-1]
            if e.status_code == 404 and self._spa and not is_api and not is_file:
                return await super().get_response("index.html", scope)
            raise


class SavitarApp(FastAPI):
    """FastAPI + Svelte 5 frontend. Every route you add is served under /api."""

    def __init__(
        self, *, web=None, dev=None, api_prefix="/api", spa=True, lifespan=None, **kwargs
    ):
        cfg, root = config.load()
        web = Path(web if web is not None else cfg.get("web", "web"))

        self._user_lifespan = lifespan
        self._mounted = False
        self.web = (web if web.is_absolute() else root / web).resolve()
        self.dev = config.resolve_dev(dev, cfg)
        self.packages = list(cfg.get("packages", []))
        self.api_prefix = api_prefix
        self.spa = spa
        self.out = out_dir(self.web)

        if not (self.web / "App.svelte").exists():
            raise FileNotFoundError(f"savitar: {self.web / 'App.svelte'} not found")

        super().__init__(lifespan=self._savitar_lifespan, **kwargs)
        # docs/openapi are already registered; everything after this gets the prefix
        self.router.prefix = api_prefix

    @asynccontextmanager
    async def _savitar_lifespan(self, app):
        proc = None
        out = self.out

        if self.dev:  # single process only: watch + rebuild
            check_venv()
            bun = find_bun()
            ensure_deps(bun, self.packages)
            out.mkdir(parents=True, exist_ok=True)
            ready = out.parent / ".ready"
            ready.unlink(missing_ok=True)
            proc = subprocess.Popen(
                [bun, str(BUILD_JS)], env={**build_env(self.web, out), "WATCH": "1"}
            )
            t0 = time.monotonic()  # wait for the first build so page loads aren't stale/404
            while proc.poll() is None and not ready.exists() and time.monotonic() - t0 < 30:
                await asyncio.sleep(0.1)
        elif not (out / "index.html").exists():
            # prod: workers only serve, build once beforehand
            raise RuntimeError(
                "savitar: no build found. Run `savitar build`, "
                "or enable dev (SAVITAR_DEV=1 or [tool.savitar] dev = true)"
            )

        out.mkdir(parents=True, exist_ok=True)
        if not self._mounted:  # must be last so /api/* wins
            self.mount(
                "/",
                _Static(directory=out, html=True, api_prefix=self.api_prefix, spa=self.spa),
                name="savitar-web",
            )
            self._mounted = True

        try:
            if self._user_lifespan:
                async with self._user_lifespan(app):
                    yield
            else:
                yield
        finally:
            if proc:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()


class Savitar:
    @staticmethod
    def app(**kwargs) -> SavitarApp:
        return SavitarApp(**kwargs)
