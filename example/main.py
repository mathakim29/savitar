from savitar import Savitar

app = Savitar.app()


@app.get("/todos")  # -> /api/todos
def todos():
    return [{"title": "learn svelte"}, {"title": "ship it"}]
