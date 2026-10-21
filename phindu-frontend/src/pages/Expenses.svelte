<script>
  import { onMount } from 'svelte';
  import { Receipt, CheckCircle2, AlertCircle } from 'lucide-svelte';
  import Layout from '../components/Layout.svelte';
  import API from '../api/api';

  let name = '';
  let amount = '';
  let category = '';
  let loading = false;
  let message = '';
  let messageType = ''; // 'success' | 'error'
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
      message = 'Name and amount are required.';
      messageType = 'error';
      return;
    }

    loading = true;
    message = '';

    try {
      // 🔧 FIX: send JSON body, not query params (matches fixed backend)
      await API.post('/expenses/', {
        name: name.trim(),
        amount: parseFloat(amount),
        category: category.trim() || 'Uncategorized',
      });
      message = 'Expense recorded successfully!';
      messageType = 'success';
      name = '';
      amount = '';
      category = '';
      await fetchExpenses();
    } catch (err) {
      message = err.response?.data?.detail || 'Failed to record expense. Please try again.';
      messageType = 'error';
    } finally {
      loading = false;
    }
  }
</script>

<Layout title="Expenses">
  <div class="page-wrapper">
    <div class="card expense-card">
      <h2>
        <Receipt size={20} strokeWidth={2} />
        Record New Expense
      </h2>
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
          <div class="message" class:error={messageType === 'error'}>
            {#if messageType === 'error'}
              <AlertCircle size={16} strokeWidth={2} />
            {:else}
              <CheckCircle2 size={16} strokeWidth={2} />
            {/if}
            <span>{message}</span>
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

    <div class="card expenses-list">
      <h3>Recent Expenses</h3>
      {#if expenses.length === 0}
        <p class="empty-text">No expenses recorded.</p>
      {:else}
        <div class="table-wrapper">
          <table>
            <thead>
              <tr><th>Name</th><th>Amount</th><th>Category</th><th>Date</th></tr>
            </thead>
            <tbody>
              {#each expenses as exp}
                <tr>
                  <td>{exp.name}</td>
                  <td><strong>MWK {exp.amount?.toLocaleString()}</strong></td>
                  <td>{exp.category}</td>
                  <td>{new Date(exp.created_at).toLocaleDateString()}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  </div>
</Layout>

<style>
  .page-wrapper {
    max-width: 700px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }
  .card {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 12px;
    padding: 1.25rem;
  }
  .expense-card h2 {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0;
    margin-bottom: 1.25rem;
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--text, #111827);
  }
  .form-group {
    margin-bottom: 1rem;
  }
  label {
    display: block;
    margin-bottom: 0.4rem;
    font-weight: 500;
    font-size: 0.9rem;
    color: var(--text, #111827);
  }
  input {
    width: 100%;
    padding: 0.65rem 0.85rem;
    font-size: 0.95rem;
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    background: var(--surface, #fff);
    color: var(--text, #111827);
    box-sizing: border-box;
  }
  input:focus {
    outline: none;
    border-color: var(--primary, #0f6b3e);
    box-shadow: 0 0 0 3px rgba(15, 107, 62, 0.1);
  }
  .form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.75rem;
  }
  .message {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 1rem 0;
    padding: 0.65rem 0.85rem;
    border-radius: 8px;
    background: #dcfce7;
    color: #166534;
    font-size: 0.88rem;
  }
  .message.error {
    background: #fee2e2;
    color: #991b1b;
  }
  .btn {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.6rem 1rem;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    font-weight: 500;
    font-size: 0.9rem;
  }
  .btn-primary {
    background: var(--primary, #0f6b3e);
    color: white;
  }
  .btn-primary:hover:not(:disabled) {
    background: var(--primary-dark, #0a4f2e);
  }
  .btn-primary:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
  .btn-block {
    width: 100%;
    justify-content: center;
    padding: 0.75rem;
  }
  .spinner {
    width: 14px;
    height: 14px;
    border: 2px solid rgba(255, 255, 255, 0.4);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  .expenses-list h3 {
    margin-top: 0;
    margin-bottom: 1rem;
    font-size: 1rem;
    font-weight: 600;
  }
  .empty-text {
    text-align: center;
    padding: 1.5rem;
    color: var(--text-light, #6b7280);
    font-size: 0.9rem;
  }
  .table-wrapper {
    overflow-x: auto;
    border-radius: 8px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
  }
  th,
  td {
    text-align: left;
    padding: 0.6rem 0.5rem;
    border-bottom: 1px solid var(--border, #e5e7eb);
  }
  th {
    background: var(--background, #f9fafb);
    font-weight: 600;
    color: var(--text-light, #6b7280);
    font-size: 0.78rem;
    text-transform: uppercase;
  }

  @media (max-width: 480px) {
    .form-row {
      grid-template-columns: 1fr;
      gap: 0;
    }
    .card {
      padding: 1rem;
    }
    th,
    td {
      padding: 0.45rem 0.35rem;
      font-size: 0.82rem;
    }
  }
</style>