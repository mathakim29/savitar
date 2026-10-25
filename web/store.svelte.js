export const todos = $state({ items: [], loading: false });

export async function load() {
  todos.loading = true;
  todos.items = await (await fetch("/api/todos")).json();
  todos.loading = false;
}
