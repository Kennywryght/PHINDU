<script>
  import Layout from '../components/Layout.svelte';
  import API from '../api/api';

  let name = '';
  let amount = '';
  let category = '';
  let loading = false;
  let message = '';
  let expenses = [];

  onMount(fetchExpenses);
  async function fetchExpenses() {
    try {
      const res = await API.get('/expenses/');
      expenses = res.data;
    } catch (err) {
      console.error('Failed to fetch expenses', err);
    }
  }

  async function handleSubmit() {
    if (!name.trim() || !amount) {
      message = '❌ Name and amount are required.';
      return;
    }

    loading = true;
    message = '';

    try {
      await API.post(
        `/expenses/?name=${encodeURIComponent(name)}&amount=${amount}&category=${encodeURIComponent(category)}`
      );
      message = '✅ Expense recorded successfully!';
      name = '';
      amount = '';
      category = '';
    } catch (err) {
      message = '❌ Failed to record expense. Please try again.';
      console.error(err);
    } finally {
      loading = false;
    }
  }
</script>

<Layout title="Expenses">
  <div class="page-wrapper">
    <div class="card expense-card">
      <h2>💸 Record New Expense</h2>
      <form on:submit|preventDefault={handleSubmit}>
        <div class="form-group">
          <label for="name">Expense Name</label>
          <input
            id="name"
            type="text"
            bind:value={name}
            placeholder="e.g., Rent, Supplies, Utilities"
            disabled={loading}
          />
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="amount">Amount (MWK)</label>
            <input
              id="amount"
              type="number"
              min="0"
              step="0.01"
              bind:value={amount}
              placeholder="0.00"
              disabled={loading}
            />
          </div>

          <div class="form-group">
            <label for="category">Category</label>
            <input
              id="category"
              type="text"
              bind:value={category}
              placeholder="Operations, Marketing, etc."
              disabled={loading}
            />
          </div>
        </div>

        {#if message}
          <div class="message" class:error={message.startsWith('❌')}>
            {message}
          </div>
        {/if}

        <button type="submit" class="btn btn-primary btn-block" disabled={loading}>
          {#if loading}
            <span class="spinner"></span> Saving...
          {:else}
            Save Expense
          {/if}
        </button>
      </form>
    </div>
    <div class="expenses-list card">
      <h3>Recent Expenses</h3>
      {#if expenses.length === 0}
        <p>No expenses recorded.</p>
      {:else}
        <table>
          <thead>
            <tr><th>Name</th><th>Amount</th><th>Category</th><th>Date</th></tr>
          </thead>
          <tbody>
            {#each expenses as exp}
              <tr>
                <td>{exp.name}</td>
                <td>MWK {exp.amount}</td>
                <td>{exp.category}</td>
                <td>{new Date(exp.created_at).toLocaleDateString()}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>
  </div>
</Layout>

<style>
  .page-wrapper {
    max-width: 600px;
    margin: 0 auto;
  }

  .expense-card {
    padding: 2rem;
  }

  h2 {
    margin-bottom: 2rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .form-group {
    margin-bottom: 1.5rem;
  }

  label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: var(--text);
  }

  input {
    width: 100%;
    padding: 0.75rem 1rem;
    font-size: 1rem;
  }

  .form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }

  .message {
    margin: 1rem 0;
    padding: 0.75rem;
    border-radius: var(--radius);
    background: #dcfce7;
    color: #166534;
  }

  .message.error {
    background: #fee2e2;
    color: #991b1b;
  }

  .btn-block {
    width: 100%;
    justify-content: center;
    padding: 0.875rem;
  }

  .spinner {
    display: inline-block;
    width: 1rem;
    height: 1rem;
    border: 2px solid white;
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  @media (max-width: 480px) {
    .form-row {
      grid-template-columns: 1fr;
      gap: 0;
    }
  }
</style>