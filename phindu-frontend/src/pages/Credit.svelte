<script>
  import { onMount } from 'svelte';
  import { CreditCard, DollarSign, PartyPopper } from 'lucide-svelte';
  import Layout from '../components/Layout.svelte';
  import API from '../api/api';

  let debtors = [];
  let loading = true;
  let showPaymentModal = false;
  let selectedDebtor = null;
  let paymentAmount = 0;

  onMount(fetchDebtors);

  async function fetchDebtors() {
    loading = true;
    try {
      const res = await API.get('/customers/debtors');
      debtors = res.data;
    } catch (err) {
      console.error('Failed to fetch debtors', err);
    } finally {
      loading = false;
    }
  }

  function openPaymentModal(debtor) {
    selectedDebtor = debtor;
    paymentAmount = 0;
    showPaymentModal = true;
  }

  async function recordPayment() {
    if (!selectedDebtor || paymentAmount <= 0) return;
    try {
      await API.post(`/customers/${selectedDebtor.id}/record-payment`, null, {
        params: { amount: paymentAmount },
      });
      await fetchDebtors();
      showPaymentModal = false;
    } catch (err) {
      alert('Payment failed');
    }
  }
</script>

<Layout title="Credit / Loans">
  <div class="credit-page">
    <div class="page-header">
      <h2>
        <CreditCard size={22} strokeWidth={2} />
        Outstanding Credit
      </h2>
      <p class="subtitle">Customers who owe money</p>
    </div>

    {#if loading}
      <p class="state-text">Loading...</p>
    {:else if debtors.length === 0}
      <div class="card empty-card">
        <PartyPopper size={48} strokeWidth={1.5} class="celebrate-icon" />
        <h3>No outstanding credit</h3>
        <p>Every customer is settled up.</p>
      </div>
    {:else}
      <!-- Desktop table -->
      <div class="table-wrapper desktop-only">
        <table class="debtors-table">
          <thead>
            <tr>
              <th>Customer</th>
              <th>Phone</th>
              <th>Amount Owed</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {#each debtors as debtor}
              <tr>
                <td><strong>{debtor.name}</strong></td>
                <td>{debtor.phone || '—'}</td>
                <td><strong class="amount">MWK {debtor.total_credit?.toLocaleString()}</strong></td>
                <td>
                  <button class="btn btn-sm btn-primary" on:click={() => openPaymentModal(debtor)} type="button">
                    <DollarSign size={14} strokeWidth={2} /> Record Payment
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Mobile cards -->
      <div class="mobile-debtors">
        {#each debtors as debtor}
          <div class="debtor-card">
            <div class="debtor-header">
              <h3>{debtor.name}</h3>
              <span class="amount">MWK {debtor.total_credit?.toLocaleString()}</span>
            </div>
            <p class="phone-line">{debtor.phone || 'No phone'}</p>
            <button class="btn btn-primary btn-block" on:click={() => openPaymentModal(debtor)} type="button">
              <DollarSign size={14} strokeWidth={2} /> Record Payment
            </button>
          </div>
        {/each}
      </div>
    {/if}
  </div>

  {#if showPaymentModal}
    <div class="modal-overlay" role="dialog" aria-modal="true" tabindex="-1" on:click|self={() => (showPaymentModal = false)}>
      <div class="modal">
        <h3>
          <DollarSign size={18} strokeWidth={2} />
          Record Payment — {selectedDebtor?.name}
        </h3>
        <p class="modal-info">Current balance: MWK {selectedDebtor?.total_credit?.toLocaleString()}</p>
        <div class="form-group">
          <label for="paymentAmt">Amount (MWK)</label>
          <input
            id="paymentAmt"
            type="number"
            min="0"
            step="0.01"
            max={selectedDebtor?.total_credit}
            bind:value={paymentAmount}
          />
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" on:click={() => (showPaymentModal = false)} type="button">Cancel</button>
          <button class="btn btn-primary" on:click={recordPayment} type="button">Save</button>
        </div>
      </div>
    </div>
  {/if}
</Layout>

<style>
  .credit-page {
    max-width: 900px;
    margin: 0 auto;
  }
  .page-header {
    margin-bottom: 1.25rem;
  }
  .page-header h2 {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 0;
    font-size: 1.2rem;
    font-weight: 600;
    color: var(--text, #111827);
  }
  .subtitle {
    color: var(--text-light, #6b7280);
    margin-top: 0.25rem;
    font-size: 0.88rem;
  }
  .state-text {
    text-align: center;
    padding: 2rem;
    color: var(--text-light, #6b7280);
  }
  .card {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 12px;
    padding: 1.25rem;
  }
  .empty-card {
    text-align: center;
    padding: 2.5rem 1.5rem;
  }
  .celebrate-icon {
    color: var(--success, #16a34a);
    margin-bottom: 0.75rem;
  }
  .empty-card h3 {
    margin: 0 0 0.4rem;
    font-size: 1.05rem;
    color: var(--text, #111827);
  }
  .empty-card p {
    color: var(--text-light, #6b7280);
    margin: 0;
    font-size: 0.9rem;
  }
  .table-wrapper {
    overflow-x: auto;
    background: var(--surface, #fff);
    border-radius: 10px;
    border: 1px solid var(--border, #e5e7eb);
  }
  .debtors-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
  }
  .debtors-table th {
    text-align: left;
    padding: 0.7rem 0.75rem;
    background: var(--background, #f9fafb);
    font-weight: 600;
    color: var(--text-light, #6b7280);
    font-size: 0.78rem;
    text-transform: uppercase;
  }
  .debtors-table td {
    padding: 0.7rem 0.75rem;
    border-top: 1px solid var(--border, #e5e7eb);
    color: var(--text, #111827);
  }
  .amount {
    color: var(--danger, #dc2626);
    font-weight: 700;
  }
  .mobile-debtors {
    display: none;
    flex-direction: column;
    gap: 0.65rem;
  }
  .debtor-card {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 10px;
    padding: 1rem;
  }
  .debtor-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.35rem;
  }
  .debtor-header h3 {
    margin: 0;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text, #111827);
  }
  .phone-line {
    font-size: 0.85rem;
    color: var(--text-light, #6b7280);
    margin: 0 0 0.75rem;
  }
  .btn {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.5rem 0.9rem;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    font-weight: 500;
    font-size: 0.85rem;
  }
  .btn-primary {
    background: var(--primary, #0f6b3e);
    color: white;
  }
  .btn-primary:hover {
    background: var(--primary-dark, #0a4f2e);
  }
  .btn-secondary {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    color: var(--text, #111827);
  }
  .btn-sm {
    padding: 0.4rem 0.75rem;
    font-size: 0.82rem;
  }
  .btn-block {
    width: 100%;
    justify-content: center;
    padding: 0.55rem;
  }
  .modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    padding: 1rem;
  }
  .modal {
    background: var(--surface, #fff);
    border-radius: 12px;
    padding: 1.25rem;
    max-width: 400px;
    width: 100%;
    max-height: 90vh;
    overflow-y: auto;
  }
  .modal h3 {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0;
    margin-bottom: 0.5rem;
    font-size: 1.05rem;
    color: var(--text, #111827);
  }
  .modal-info {
    font-size: 0.85rem;
    color: var(--text-light, #6b7280);
    margin: 0 0 1rem;
  }
  .form-group {
    margin-bottom: 0.85rem;
  }
  label {
    display: block;
    margin-bottom: 0.3rem;
    font-weight: 500;
    font-size: 0.88rem;
    color: var(--text, #111827);
  }
  input {
    width: 100%;
    padding: 0.6rem;
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    font-size: 0.9rem;
    background: var(--surface, #fff);
    color: var(--text, #111827);
    box-sizing: border-box;
  }
  input:focus {
    outline: none;
    border-color: var(--primary, #0f6b3e);
    box-shadow: 0 0 0 3px rgba(15, 107, 62, 0.1);
  }
  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.6rem;
    margin-top: 1rem;
  }

  @media (max-width: 768px) {
    .desktop-only {
      display: none;
    }
    .mobile-debtors {
      display: flex;
    }
  }
</style>