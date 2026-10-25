import os
import shutil
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

BUILD_JS = Path(__file__).parent / "build.js"
VENV = Path(sys.prefix)  # whatever venv uv is using
OUT = VENV / "savitar" / "web"  # build output (generated, don't edit)


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


def ensure_svelte(bun: str) -> None:
    """svelte lives in <venv>/node_modules."""
    if not (VENV / "node_modules" / "svelte" / "package.json").exists():
        subprocess.run([bun, "add", "svelte", "--cwd", str(VENV)], check=True)


def build_env(web: Path) -> dict:
    return {**os.environ, "VIRTUAL_ENV": str(VENV), "SAVITAR_SRC": str(web)}


class SavitarApp(FastAPI):
    """FastAPI + Svelte 5 frontend. Every route you add is served under /api."""

    def __init__(self, *, web="web", dev=None, api_prefix="/api", lifespan=None, **kwargs):
        self._user_lifespan = lifespan
        self._mounted = False
        self.web = Path(web).resolve()
        self.dev = (os.environ.get("SAVITAR_DEV", "1") == "1") if dev is None else dev

        if not (self.web / "App.svelte").exists():
            raise FileNotFoundError(f"savitar: {self.web / 'App.svelte'} not found")

        super().__init__(lifespan=self._savitar_lifespan, **kwargs)
        # docs/openapi are already registered; everything after this gets the prefix
        self.router.prefix = api_prefix

    @asynccontextmanager
    async def _savitar_lifespan(self, app):
        proc = None
        if self.dev:  # single process only: watch + rebuild
            bun = find_bun()
            ensure_svelte(bun)
            OUT.mkdir(parents=True, exist_ok=True)
            proc = subprocess.Popen(
                [bun, str(BUILD_JS)], env={**build_env(self.web), "WATCH": "1"}
            )
        elif not (OUT / "index.html").exists():
            # prod: workers only serve, build once beforehand
            raise RuntimeError("savitar: run `savitar build` first")

        OUT.mkdir(parents=True, exist_ok=True)
        if not self._mounted:  # must be last so /api/* wins
            self.mount("/", StaticFiles(directory=OUT, html=True), name="savitar-web")
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


class Savitar:
    @staticmethod
    def app(**kwargs) -> SavitarApp:
        return SavitarApp(**kwargs)
