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

- `uv add savitar` (or `uv add ./path/to/savitar` for a local copy)
- Deps: `fastapi[standard]`, `bun-wheel` (provides `bun` in `<venv>/bin`)
- No system bun or node needed
- svelte auto-installs into `<venv>/node_modules` on first start

## Project layout

```
main.py
web/
  App.svelte          <- required entry
  store.svelte.js     <- rune modules (any *.svelte.js / *.svelte.ts)
  Other.svelte
```

## Run

- Dev (single process, rebuilds on change, refresh the browser manually):
  `uv run fastapi dev main.py`
- Prod (build once, then any number of workers):
  ```
  uv run savitar build            # or: uv run savitar build ui
  SAVITAR_DEV=0 uv run fastapi run main.py --workers 4
  ```
- Prod workers do not need bun at runtime, only at build time
- Forgot to build? Workers fail on startup with `run savitar build first`

Package management

Use `savitar pkg` to run Bun in the active uv environment. For example:

```sh
uv run savitar pkg add svelte
uv run savitar pkg remove svelte
```

This is equivalent to running Bun with `--cwd "$(uv run python -c 'import sys;print(sys.prefix)')"`.

## API

`Savitar.app(web="web", dev=None, api_prefix="/api", lifespan=None, **fastapi_kwargs)`

- `web`: frontend folder (needs `App.svelte`)
- `dev`: `True` watch+rebuild, `False` serve only. Default: env `SAVITAR_DEV` (`1` if unset)
- `api_prefix`: prefix for all routes. `""` = plain FastAPI plus frontend
- `lifespan`: yours, wrapped (not replaced)
- Anything else goes to `FastAPI(...)`

## Behavior

- Decorator routes and `include_router` routes get `/api`
- `/docs`, `/openapi.json` stay at the root
- Frontend is mounted at `/` on startup, after your routes
- Lifespan order. Startup: Savitar, then yours. Shutdown: yours, then Savitar
- Frontend calls the API with relative URLs: `fetch("/api/todos")`

## Files

- Build output: `<venv>/savitar/web` (generated)
- Temp entry: `<venv>/savitar/.entry.js` (generated)
- Compiler/runtime: `<venv>/node_modules/svelte`

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
- Run with a different Python than uv's (svelte installs into that venv)

Run
- Use `--workers N` in dev (each worker would spawn its own build)
- Use `--reload` with `SAVITAR_DEV=0` and expect rebuilds
- Forget `savitar build` before prod workers
- Name your own object `Savitar`

## Troubleshooting

- `bun not found`: run through `uv run`, or reinstall (`uv sync`)
- `Could not resolve "svelte/..."`: the exports resolver in `src/savitar/build.js` (`sv()`); check `<venv>/node_modules/svelte/package.json`
- Blank page in prod: build missing or stale, run `savitar build`
- Compile error: shown in the server console (dev) or fails `savitar build` (prod)
- Status: untested, report resolver or `/api` prefix issues first
