<script>
  import { onMount } from 'svelte';
  import axios from 'axios';

  let data = null;
  let loading = true;
  let error = null;

  onMount(async () => {
    try {
      const response = await axios.get('https://jsonplaceholder.typicode.com');
      data = response.data;
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  });
</script>

{#if loading}
  <p>Loading...</p>
{:else if error}
  <p>Error: {error}</p>
{:else}
  <pre>{JSON.stringify(data, null, 2)}</pre>
{/if}
