# savitar

FastAPI + Svelte 5 (runes). Bun compiles the frontend. Everything generated lives in your venv.

```python
from savitar import Savitar

app = Savitar.app()  # a FastAPI subclass

@app.get("/todos")   # served at /api/todos
def todos():
    return [{"title": "hi"}]
```

## Install
```bash
uv add https://github.com/mathakim29/savitar.git
```




### Notes:
- No system bun or node needed by default (preinstalled with bun-wheels)
- svelte (and your `packages`) auto-install into `<venv>/node_modules` on first start/build
- Needs a virtualenv (`uv run`); refuses to run against system Python

## Project layout

```
main.py
pyproject.toml        <- [tool.savitar] settings
web/
  App.svelte          <- required entry
  store.svelte.js     <- rune modules (any *.svelte.js / *.svelte.ts)
  Other.svelte
```

## Settings

Your `pyproject.toml`:

```toml
[tool.savitar]
web = "web"      # frontend folder, relative to pyproject.toml
dev = false      # default false: serve a prebuilt frontend
packages = []    # extra JS packages (managed by `savitar pkg`)
```

Precedence for `dev`: `Savitar.app(dev=...)` > env `SAVITAR_DEV` > `[tool.savitar] dev` > `false`.

## Run

- Prod (default): build once, then any number of workers
  ```
  uv run savitar build            # or: uv run savitar build ui
  uv run fastapi run main.py --workers 4
  ```
- Dev (single process, rebuilds on change, refresh the browser manually):
  `SAVITAR_DEV=1 uv run fastapi dev main.py`
  or set `dev = true` in `[tool.savitar]`
- Prod workers need bun only at build time
- No build and dev off? Startup fails with `no build found`
- Dev waits for the first build before serving

## Packages

`savitar pkg` runs Bun in the active venv and records packages in `[tool.savitar] packages`.
If the venv is recreated, they are reinstalled automatically on next start/build.

```sh
uv run savitar pkg add blockly
uv run savitar pkg add blockly@11
uv run savitar pkg remove blockly
```

Then `import Blockly from "blockly"` in Svelte files. Other Bun commands pass through unrecorded.
Project-local `node_modules` (next to `web/`) wins over the venv if both have a package.

To run any Bun command with the active venv as its working directory:

```sh
uv run savitar exec run script.ts
uv run savitar exec test
```

Arguments are passed through to Bun; `savitar` supplies `--cwd <venv>`.

## API

`Savitar.app(web=None, dev=None, api_prefix="/api", spa=True, lifespan=None, **fastapi_kwargs)`

- `web`: frontend folder (needs `App.svelte`). Default from settings, else `web`
- `dev`: see Settings
- `api_prefix`: prefix for all routes. `""` = plain FastAPI plus frontend
- `spa`: unknown non-file, non-api paths return `index.html` (client-side routing). `False` = 404
- `lifespan`: yours, wrapped (not replaced)
- Anything else goes to `FastAPI(...)`

## Behavior

- Decorator routes and `include_router` routes get `/api`
- `/docs`, `/openapi.json` stay at the root
- Frontend is mounted at `/` on startup, after your routes
- Lifespan order. Startup: Savitar, then yours. Shutdown: yours, then Savitar
- Frontend calls the API with relative URLs: `fetch("/api/todos")`
- Component `<style>` blocks work (injected); prod bundles are minified

## Files

- Build output: `<venv>/savitar/<hash>/web` (one per frontend folder, generated)
- Temp: `<venv>/savitar/<hash>/.entry.js`, `.ready` (generated)
- Compiler/runtime and packages: `<venv>/node_modules`

## Do NOT

Routes
- Write `/api` in route paths (you'd get `/api/api/...`)
- `app.mount("/", ...)`, it belongs to the frontend
- Expect `app.mount()` / `app.add_route()` to get `/api` (they don't)
- Add routes after startup (frontend mount must stay last)

Lifespan
- Set `app.router.lifespan_context`
- Pass `lifespan=` anywhere except `Savitar.app()`

Frontend
- Rename or delete `web/App.svelte`
- Import without the full extension (`./store.svelte.js`)
- Use `$state` / `$derived` in plain `.js` files (must be `.svelte.js`)

Venv / files
- Edit anything in `<venv>/savitar/`
- Delete `<venv>/node_modules` while the server runs
- Run with a different Python than uv's (packages install into that venv)

Run
- Use `dev = true` / `SAVITAR_DEV=1` with `--workers N` (each worker would spawn its own build)
- Forget `savitar build` before prod
- Name your own object `Savitar`

## Troubleshooting

- `bun not found`: run through `uv run`, or reinstall (`uv sync`)
- `no virtualenv active`: use `uv run`
- `Could not resolve "x"`: `uv run savitar pkg add x`
- `Could not resolve "svelte/..."`: resolver in `src/savitar/build.js` (`resolveVenv`); check `<venv>/node_modules/svelte/package.json`
- Blank page in prod: build missing or stale, run `savitar build`
- Compile error: shown in the server console (dev) or fails `savitar build` (prod)
- Dev: new packages need a server restart (only `web/` is watched)
- Dev: a hard-killed server (SIGKILL) can leave the Bun watcher running, kill it manually
- Status: untested
