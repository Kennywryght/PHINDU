<script>
  import { onMount } from "svelte";
  import {
    CreditCard,
    DollarSign,
    PartyPopper,
    ChevronDown,
    ChevronRight,
    Shield,
    ShieldAlert,
    ShieldCheck,
    ShieldQuestion,
    AlertTriangle,
    CheckCircle2,
    Info,
  } from "lucide-svelte";
  import Layout from "../components/Layout.svelte";
  import API from "../api/api";

  let debtors = [];
  let loading = true;
  let showPaymentModal = false;
  let selectedDebtor = null;
  let paymentAmount = 0;
  let expandedRisk = {}; // { customer_id: bool }

  onMount(fetchDebtors);

  async function fetchDebtors() {
    loading = true;
    try {
      const res = await API.get("/customers/debtors?include_risk=true");
      debtors = res.data;
    } catch (err) {
      console.error("Failed to fetch debtors", err);
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
      await API.post(`/customers/${selectedDebtor.id}/record-payment`, {
        amount: paymentAmount,
        method: "cash",
      });
      await fetchDebtors();
      showPaymentModal = false;
    } catch (err) {
      alert("Payment failed: " + (err.response?.data?.detail || "Unknown error"));
    }
  }

  function toggleRisk(customerId) {
    expandedRisk[customerId] = !expandedRisk[customerId];
  }

  function riskIcon(level) {
    if (level === "low") return ShieldCheck;
    if (level === "medium") return Shield;
    if (level === "high") return ShieldAlert;
    return ShieldQuestion;
  }

  function riskClass(level) {
    return `risk-${level}`;
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
        <PartyPopper size={48} strokeWidth={1.5} />
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
              <th>Risk</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {#each debtors as debtor}
              {@const RiskIcon = debtor.risk ? riskIcon(debtor.risk.level) : null}
              <tr>
                <td>
                  <button
                    class="debtor-name-btn"
                    on:click={() => debtor.risk && toggleRisk(debtor.id)}
                    type="button"
                    disabled={!debtor.risk}
                  >
                    {#if debtor.risk}
                      {#if expandedRisk[debtor.id]}
                        <ChevronDown size={14} />
                      {:else}
                        <ChevronRight size={14} />
                      {/if}
                    {/if}
                    <strong>{debtor.name}</strong>
                  </button>
                </td>
                <td>{debtor.phone || "—"}</td>
                <td><strong class="amount">MWK {debtor.total_credit?.toLocaleString()}</strong></td>
                <td>
                  {#if debtor.risk}
                    <span class="risk-badge {riskClass(debtor.risk.level)}">
                      <RiskIcon size={14} strokeWidth={2} />
                      {debtor.risk.label}
                    </span>
                  {:else}
                    <span class="muted">—</span>
                  {/if}
                </td>
                <td>
                  <button
                    class="btn btn-sm btn-primary"
                    on:click={() => openPaymentModal(debtor)}
                    type="button"
                  >
                    <DollarSign size={14} strokeWidth={2} /> Record Payment
                  </button>
                </td>
              </tr>
              {#if debtor.risk && expandedRisk[debtor.id]}
                <tr class="risk-detail-row">
                  <td colspan="5">
                    <div class="risk-detail">
                      <div class="risk-header">
                        <span class="risk-score">
                          Score: <strong>{debtor.risk.score}/100</strong>
                        </span>
                        <span class="risk-recommendation">
                          <Info size={14} /> {debtor.risk.recommendation}
                        </span>
                      </div>
                      {#if debtor.risk.warnings.length > 0}
                        <div class="risk-section">
                          <strong class="section-label">
                            <AlertTriangle size={12} /> Risk factors
                          </strong>
                          <ul class="risk-list">
                            {#each debtor.risk.warnings as warning}
                              <li class="warning-item">{warning}</li>
                            {/each}
                          </ul>
                        </div>
                      {/if}
                      {#if debtor.risk.positives.length > 0}
                        <div class="risk-section">
                          <strong class="section-label">
                            <CheckCircle2 size={12} /> Positive signals
                          </strong>
                          <ul class="risk-list">
                            {#each debtor.risk.positives as positive}
                              <li class="positive-item">{positive}</li>
                            {/each}
                          </ul>
                        </div>
                      {/if}
                      <div class="risk-factors-grid">
                        <div class="factor">
                          <span>Payments made</span>
                          <strong>{debtor.risk.factors.payment_count}</strong>
                        </div>
                        <div class="factor">
                          <span>Total sold</span>
                          <strong>MWK {debtor.risk.factors.total_sold?.toLocaleString()}</strong>
                        </div>
                        <div class="factor">
                          <span>Avg purchase</span>
                          <strong>MWK {debtor.risk.factors.avg_purchase?.toLocaleString()}</strong>
                        </div>
                        <div class="factor">
                          <span>Credit ratio</span>
                          <strong>{Math.round(debtor.risk.factors.credit_ratio * 100)}%</strong>
                        </div>
                        {#if debtor.risk.factors.avg_days_to_pay != null}
                          <div class="factor">
                            <span>Avg days to pay</span>
                            <strong>{debtor.risk.factors.avg_days_to_pay}</strong>
                          </div>
                        {/if}
                        {#if debtor.risk.factors.account_age_days != null}
                          <div class="factor">
                            <span>Account age</span>
                            <strong>{debtor.risk.factors.account_age_days}d</strong>
                          </div>
                        {/if}
                      </div>
                    </div>
                  </td>
                </tr>
              {/if}
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Mobile cards -->
      <div class="mobile-debtors">
        {#each debtors as debtor}
          {@const RiskIcon = debtor.risk ? riskIcon(debtor.risk.level) : null}
          <div class="debtor-card">
            <div class="debtor-header">
              <div class="debtor-name-block">
                <h3>{debtor.name}</h3>
                {#if debtor.risk}
                  <span class="risk-badge {riskClass(debtor.risk.level)}">
                    <RiskIcon size={12} strokeWidth={2} />
                    {debtor.risk.label}
                  </span>
                {/if}
              </div>
              <span class="amount">MWK {debtor.total_credit?.toLocaleString()}</span>
            </div>
            <p class="phone-line">{debtor.phone || "No phone"}</p>

            {#if debtor.risk}
              <button
                class="risk-toggle-btn"
                on:click={() => toggleRisk(debtor.id)}
                type="button"
              >
                {#if expandedRisk[debtor.id]}
                  Hide risk details
                {:else}
                  View risk details ({debtor.risk.score}/100)
                {/if}
              </button>

              {#if expandedRisk[debtor.id]}
                <div class="risk-detail mobile-risk-detail">
                  <div class="risk-recommendation">
                    <Info size={14} /> {debtor.risk.recommendation}
                  </div>
                  {#if debtor.risk.warnings.length > 0}
                    <ul class="risk-list">
                      {#each debtor.risk.warnings as warning}
                        <li class="warning-item">
                          <AlertTriangle size={12} /> {warning}
                        </li>
                      {/each}
                    </ul>
                  {/if}
                  {#if debtor.risk.positives.length > 0}
                    <ul class="risk-list">
                      {#each debtor.risk.positives as positive}
                        <li class="positive-item">
                          <CheckCircle2 size={12} /> {positive}
                        </li>
                      {/each}
                    </ul>
                  {/if}
                </div>
              {/if}
            {/if}

            <button
              class="btn btn-primary btn-block"
              on:click={() => openPaymentModal(debtor)}
              type="button"
            >
              <DollarSign size={14} strokeWidth={2} /> Record Payment
            </button>
          </div>
        {/each}
      </div>
    {/if}
  </div>

  {#if showPaymentModal}
    <div
      class="modal-overlay"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      on:click|self={() => (showPaymentModal = false)}
      on:keydown={(e) => e.key === "Escape" && (showPaymentModal = false)}
    >
      <div class="modal">
        <h3>
          <DollarSign size={18} strokeWidth={2} />
          Record Payment — {selectedDebtor?.name}
        </h3>
        <p class="modal-info">
          Current balance: MWK {selectedDebtor?.total_credit?.toLocaleString()}
        </p>
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
          <button
            class="btn btn-secondary"
            on:click={() => (showPaymentModal = false)}
            type="button"
          >
            Cancel
          </button>
          <button class="btn btn-primary" on:click={recordPayment} type="button">Save</button>
        </div>
      </div>
    </div>
  {/if}
</Layout>

<style>
  .credit-page {
    max-width: 1000px;
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
    vertical-align: middle;
  }
  .debtor-name-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    background: none;
    border: none;
    padding: 0;
    cursor: pointer;
    color: var(--text, #111827);
    font-size: 0.9rem;
    text-align: left;
  }
  .debtor-name-btn:disabled {
    cursor: default;
  }
  .debtor-name-btn:hover:not(:disabled) {
    color: var(--primary, #0f6b3e);
  }
  .amount {
    color: var(--danger, #dc2626);
    font-weight: 700;
  }
  .muted {
    color: var(--text-light, #6b7280);
  }

  /* ── Risk badges ── */
  .risk-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 0.2rem 0.55rem;
    border-radius: 20px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }
  .risk-low {
    background: #dcfce7;
    color: #166534;
  }
  .risk-medium {
    background: #fef3c7;
    color: #92400e;
  }
  .risk-high {
    background: #fee2e2;
    color: #991b1b;
  }
  .risk-new {
    background: var(--background, #f9fafb);
    color: var(--text-light, #6b7280);
  }

  /* ── Risk detail row ── */
  .risk-detail-row td {
    background: var(--background, #f9fafb);
    padding: 1rem;
  }
  .risk-detail {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }
  .risk-header {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem 1rem;
    align-items: center;
  }
  .risk-score {
    font-size: 0.88rem;
    color: var(--text, #111827);
  }
  .risk-recommendation {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.85rem;
    color: var(--primary, #0f6b3e);
    font-weight: 500;
    background: #f0fdf4;
    padding: 0.35rem 0.65rem;
    border-radius: 8px;
  }
  .risk-section {
    font-size: 0.85rem;
  }
  .section-label {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    margin-bottom: 0.35rem;
    color: var(--text-light, #6b7280);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }
  .risk-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
  }
  .warning-item,
  .positive-item {
    display: flex;
    align-items: flex-start;
    gap: 0.35rem;
    font-size: 0.83rem;
    padding-left: 0.25rem;
  }
  .warning-item {
    color: #9a3412;
  }
  .positive-item {
    color: #166534;
  }
  .risk-factors-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 0.5rem;
    padding-top: 0.5rem;
    border-top: 1px dashed var(--border, #e5e7eb);
  }
  .factor {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
  }
  .factor span {
    font-size: 0.72rem;
    color: var(--text-light, #6b7280);
  }
  .factor strong {
    font-size: 0.88rem;
    color: var(--text, #111827);
  }

  /* ── Mobile risk UI ── */
  .debtor-name-block {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
  }
  .risk-toggle-btn {
    width: 100%;
    padding: 0.45rem;
    background: var(--background, #f9fafb);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.78rem;
    color: var(--text, #111827);
    font-weight: 500;
    margin: 0.4rem 0;
  }
  .mobile-risk-detail {
    padding: 0.75rem;
    background: var(--background, #f9fafb);
    border-radius: 8px;
    margin-bottom: 0.75rem;
  }

  /* ── Buttons / modal / other ── */
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
    align-items: flex-start;
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