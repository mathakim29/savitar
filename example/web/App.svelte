<script>
  import { todos, load } from "./store.svelte.js";

  let count = $state(0);
  let double = $derived(count * 2);

  load();
</script>

<main style="font-family: sans-serif; text-align: center; margin-top: 50px;">
  <h1>Savitar</h1>
  <button onclick={() => count++}>Clicks: {count} (x2 = {double})</button>

  {#if todos.loading}
    <p>Loading...</p>
  {:else}
    <ul style="list-style: none; padding: 0;">
      {#each todos.items as t}<li>{t.title}</li>{/each}
    </ul>
  {/if}
</main>
