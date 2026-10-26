<script>
  import { onMount } from "svelte";
  import {
    Calendar,
    Plus,
    ChevronRight,
    ChevronDown,
    ArrowDownCircle,
    ArrowUpCircle,
    Loader2,
    CheckCircle2,
    AlertTriangle,
    Clock,
    Wallet,
  } from "lucide-svelte";
  import Layout from "../components/Layout.svelte";
  import CloseSessionModal from "../components/CloseSessionModal.svelte";
  import SessionDrawer from "../components/SessionDrawer.svelte";
  import CashMovementModal from "../components/CashMovementModal.svelte";
  import API from "../api/api";

  let sessions = [];
  let currentSession = null;
  let currentSummary = null;
  let loading = true;

  // Modals
  let showOpenModal = false;
  let showCloseModal = false;
  let showCashModal = false;
  let cashDirection = "out";
  let showDrawer = false;
  let drawerSessionId = null;

  let openingBalance = 0;

  onMount(refreshAll);

  async function refreshAll() {
    loading = true;
    try {
      const [sessRes, curRes] = await Promise.all([
        API.get("/sessions/"),
        API.get("/sessions/current").catch(() => ({ data: {} })),
      ]);
      sessions = sessRes.data || [];
      currentSession = curRes.data && curRes.data.id ? curRes.data : null;

      if (currentSession) {
        try {
          const sumRes = await API.get("/sessions/current/summary");
          currentSummary = sumRes.data;
        } catch {
          currentSummary = null;
        }
      } else {
        currentSummary = null;
      }
    } catch (err) {
      console.error("Failed to load sessions", err);
    } finally {
      loading = false;
    }
  }

  async function openSession() {
    if (openingBalance < 0) {
      alert("Opening balance cannot be negative");
      return;
    }
    try {
      await API.post("/sessions/open", null, {
        params: { opening_balance: openingBalance },
      });
      showOpenModal = false;
      openingBalance = 0;
      await refreshAll();
    } catch (err) {
      alert("Failed to open session: " + (err.response?.data?.detail || "Unknown error"));
    }
  }

  function openCashMovement(direction) {
    cashDirection = direction;
    showCashModal = true;
  }

  async function handleCashSaved() {
    showCashModal = false;
    await refreshAll();
  }

  async function handleSessionClosed() {
    showCloseModal = false;
    await refreshAll();
  }

  function openDrawer(id) {
    drawerSessionId = id;
    showDrawer = true;
  }
  function closeDrawer() {
    showDrawer = false;
    drawerSessionId = null;
  }

  // ── Group past sessions by date ──
  $: pastSessions = sessions.filter((s) => !s.is_active);

  $: groupedSessions = (() => {
    const groups = {};
    pastSessions.forEach((s) => {
      const d = s.opened_at ? new Date(s.opened_at) : null;
      const key = d
        ? d.toLocaleDateString(undefined, {
            year: "numeric",
            month: "short",
            day: "numeric",
          })
        : "Unknown date";
      if (!groups[key]) groups[key] = [];
      groups[key].push(s);
    });
    return Object.entries(groups).map(([date, items]) => ({ date, items }));
  })();

  function fmt(n) {
    return Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: 0 });
  }
  function fmtMoney(n) {
    return Number(n || 0).toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }
  function fmtTime(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function reconBadge(status) {
    switch (status) {
      case "active":
        return { label: "Active", cls: "active" };
      case "balanced":
        return { label: "Balanced", cls: "balanced" };
      case "short":
        return { label: "Short", cls: "short" };
      case "over":
        return { label: "Over", cls: "over" };
      default:
        return { label: "—", cls: "unknown" };
    }
  }
</script>

<Layout title="Daily Sessions">
  <div class="sessions-page">
    <!-- Current session card -->
    <div class="card current-session">
      <h2>
        <Calendar size={20} strokeWidth={2} />
        Current Session
      </h2>

      {#if currentSession && currentSummary}
        <!-- Drawer math strip -->
        <div class="drawer-strip">
          <div class="ds-cell">
            <span class="ds-label">Opening</span>
            <strong>MWK {fmt(currentSummary.cash_drawer.opening_balance)}</strong>
          </div>
          <div class="ds-cell">
            <span class="ds-label">Cash in</span>
            <strong class="ds-in">
              +MWK {fmt(
                (currentSummary.cash_drawer.plus_cash_sales || 0) +
                  (currentSummary.cash_drawer.plus_cash_payments_received || 0) +
                  (currentSummary.cash_drawer.plus_cash_added || 0)
              )}
            </strong>
          </div>
          <div class="ds-cell">
            <span class="ds-label">Cash out</span>
            <strong class="ds-out">
              −MWK {fmt(
                (currentSummary.cash_drawer.minus_expenses || 0) +
                  (currentSummary.cash_drawer.minus_cash_removed || 0)
              )}
            </strong>
          </div>
          <div class="ds-cell highlight">
            <span class="ds-label">In drawer</span>
            <strong>MWK {fmt(currentSummary.cash_drawer.expected_in_drawer)}</strong>
          </div>
        </div>

        <!-- Detail rows -->
        <div class="session-details">
          <div class="detail-row">
            <span>Opened</span>
            <strong>{fmtTime(currentSession.opened_at)} ({new Date(currentSession.opened_at).toLocaleDateString()})</strong>
          </div>
          <div class="detail-row">
            <span>Sales today</span>
            <strong>{currentSummary.sales.total_count} · MWK {fmt(currentSummary.sales.total_sales)}</strong>
          </div>
          <div class="detail-row">
            <span>Credit sales</span>
            <strong>MWK {fmt(currentSummary.sales.credit_sales)}</strong>
          </div>
          <div class="detail-row">
            <span>Expenses today</span>
            <strong>{currentSummary.expenses.count} · MWK {fmt(currentSummary.expenses.total)}</strong>
          </div>
          {#if currentSummary.payments_received.count > 0}
            <div class="detail-row">
              <span>Customer payments</span>
              <strong>{currentSummary.payments_received.count} · MWK {fmt(currentSummary.payments_received.total)}</strong>
            </div>
          {/if}
        </div>

        <!-- Cash movement buttons -->
        <div class="cash-buttons">
          <button
            class="btn btn-secondary btn-cash"
            on:click={() => openCashMovement("out")}
            type="button"
          >
            <ArrowDownCircle size={16} strokeWidth={2} /> Cash Out
          </button>
          <button
            class="btn btn-secondary btn-cash"
            on:click={() => openCashMovement("in")}
            type="button"
          >
            <ArrowUpCircle size={16} strokeWidth={2} /> Cash In
          </button>
        </div>

        <button
          class="btn btn-primary btn-block"
          on:click={() => (showCloseModal = true)}
          type="button"
        >
          Close Day
        </button>
      {:else if currentSession}
        <div class="loading-row">
          <Loader2 size={18} class="spin" /> Loading summary…
        </div>
      {:else}
        <p class="no-session">No active session.</p>
        <button
          class="btn btn-primary btn-block"
          on:click={() => (showOpenModal = true)}
          type="button"
        >
          <Plus size={16} strokeWidth={2} /> Open New Session
        </button>
      {/if}
    </div>

    <!-- Past sessions -->
    <div class="card past-sessions">
      <h2>Past Sessions</h2>
      {#if loading && sessions.length === 0}
        <div class="loading-row">
          <Loader2 size={18} class="spin" /> Loading…
        </div>
      {:else if pastSessions.length === 0}
        <p class="empty-text">No past sessions recorded.</p>
      {:else}
        {#each groupedSessions as group}
          <div class="session-group">
            <h3 class="group-date">{group.date}</h3>
            {#each group.items as s}
              {@const badge = reconBadge(s.reconciliation_status)}
              <button
                class="session-row"
                on:click={() => openDrawer(s.id)}
                type="button"
              >
                <div class="sr-left">
                  <Clock size={16} strokeWidth={2} class="sr-icon" />
                  <div class="sr-time">
                    <span class="sr-range">
                      {fmtTime(s.opened_at)} → {fmtTime(s.closed_at)}
                    </span>
                    <span class="sr-meta">
                      Sales MWK {fmt(s.total_sales)} · Expenses MWK {fmt(s.total_expenses)}
                    </span>
                  </div>
                </div>
                <div class="sr-right">
                  <span class="recon-badge {badge.cls}">{badge.label}</span>
                  {#if s.reconciliation_status === "short"}
                    <span class="sr-diff negative">
                      −MWK {fmt(Math.abs(s.cash_discrepancy))}
                    </span>
                  {:else if s.reconciliation_status === "over"}
                    <span class="sr-diff positive">
                      +MWK {fmt(s.cash_discrepancy)}
                    </span>
                  {:else if s.closing_balance !== null}
                    <span class="sr-count">MWK {fmt(s.closing_balance)} counted</span>
                  {/if}
                  <ChevronRight size={16} strokeWidth={2} class="sr-chev" />
                </div>
              </button>
            {/each}
          </div>
        {/each}
      {/if}
    </div>
  </div>
</Layout>

{#if showOpenModal}
  <div
    class="modal-overlay"
    role="dialog"
    aria-modal="true"
    tabindex="-1"
    on:click|self={() => (showOpenModal = false)}
    on:keydown={(e) => e.key === "Escape" && (showOpenModal = false)}
  >
    <div class="modal">
      <h3>
        <Calendar size={18} strokeWidth={2} /> Open New Session
      </h3>
      <div class="form-group">
        <label for="opening">Opening Cash Balance (MWK)</label>
        <input id="opening" type="number" min="0" step="0.01" bind:value={openingBalance} />
      </div>
      <div class="modal-actions">
        <button class="btn btn-secondary" on:click={() => (showOpenModal = false)} type="button">
          Cancel
        </button>
        <button class="btn btn-primary" on:click={openSession} type="button">Open</button>
      </div>
    </div>
  </div>
{/if}

{#if showCloseModal}
  <CloseSessionModal on:closed={handleSessionClosed} on:close={() => (showCloseModal = false)} />
{/if}

{#if showCashModal}
  <CashMovementModal
    direction={cashDirection}
    on:saved={handleCashSaved}
    on:close={() => (showCashModal = false)}
  />
{/if}

{#if showDrawer && drawerSessionId}
  <SessionDrawer sessionId={drawerSessionId} on:close={closeDrawer} />
{/if}

<style>
  .sessions-page {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    max-width: 900px;
    margin: 0 auto;
  }
  .card {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 12px;
    padding: 1.25rem;
  }
  .card h2 {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0;
    margin-bottom: 1rem;
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--text, #111827);
  }

  .drawer-strip {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.5rem;
    padding: 0.7rem;
    background: var(--background, #f9fafb);
    border-radius: 10px;
    margin-bottom: 0.85rem;
  }
  .ds-cell {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    min-width: 0;
  }
  .ds-label {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-weight: 700;
    color: var(--text-light, #6b7280);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .ds-cell strong {
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--text, #111827);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .ds-in {
    color: #166534 !important;
  }
  .ds-out {
    color: #b91c1c !important;
  }
  .ds-cell.highlight strong {
    color: var(--primary, #0f6b3e) !important;
    font-size: 1rem;
  }

  .session-details {
    margin: 0.5rem 0 1rem;
  }
  .detail-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--border, #e5e7eb);
    font-size: 0.88rem;
    gap: 0.5rem;
  }
  .detail-row:last-child {
    border-bottom: none;
  }
  .detail-row span {
    color: var(--text-light, #6b7280);
  }
  .detail-row strong {
    color: var(--text, #111827);
    text-align: right;
    word-break: break-word;
  }

  .cash-buttons {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.5rem;
    margin-bottom: 0.6rem;
  }
  .btn-cash {
    justify-content: center;
    padding: 0.55rem;
  }

  .no-session {
    color: var(--text-light, #6b7280);
    margin: 1rem 0;
    font-size: 0.9rem;
  }
  .loading-row {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 1.5rem;
    color: var(--text-light, #6b7280);
    font-size: 0.9rem;
  }
  .empty-text {
    text-align: center;
    padding: 1.5rem;
    color: var(--text-light, #6b7280);
    font-size: 0.9rem;
  }

  .btn {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.55rem 1rem;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    font-weight: 500;
    font-size: 0.9rem;
    transition: all 0.15s;
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
  .btn-secondary:hover {
    border-color: var(--primary, #0f6b3e);
    color: var(--primary, #0f6b3e);
  }
  .btn-block {
    width: 100%;
    justify-content: center;
    padding: 0.7rem;
  }
  .spin {
    animation: spin 1s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  /* Past sessions */
  .session-group {
    margin-bottom: 1rem;
  }
  .session-group:last-child {
    margin-bottom: 0;
  }
  .group-date {
    margin: 0 0 0.5rem;
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-light, #6b7280);
    padding: 0 0.2rem;
  }
  .session-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.75rem;
    width: 100%;
    padding: 0.7rem 0.85rem;
    margin-bottom: 0.4rem;
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 10px;
    cursor: pointer;
    text-align: left;
    transition: all 0.15s;
  }
  .session-row:hover {
    border-color: var(--primary, #0f6b3e);
    background: var(--background, #f9fafb);
  }
  .sr-left {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    min-width: 0;
    flex: 1;
  }
  .sr-icon {
    color: var(--text-light, #6b7280);
    flex-shrink: 0;
  }
  .sr-time {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    min-width: 0;
  }
  .sr-range {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--text, #111827);
  }
  .sr-meta {
    font-size: 0.75rem;
    color: var(--text-light, #6b7280);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .sr-right {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-shrink: 0;
  }
  .sr-diff {
    font-size: 0.78rem;
    font-weight: 700;
  }
  .sr-diff.negative {
    color: #b91c1c;
  }
  .sr-diff.positive {
    color: #166534;
  }
  .sr-count {
    font-size: 0.75rem;
    color: var(--text-light, #6b7280);
  }
  .sr-chev {
    color: var(--text-light, #6b7280);
    flex-shrink: 0;
  }

  .recon-badge {
    display: inline-block;
    font-size: 0.68rem;
    font-weight: 700;
    padding: 0.15rem 0.5rem;
    border-radius: 10px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    border: 1px solid;
  }
  .recon-badge.balanced {
    background: rgba(22, 163, 74, 0.1);
    color: #166534;
    border-color: #86efac;
  }
  .recon-badge.short {
    background: rgba(220, 38, 38, 0.1);
    color: #991b1b;
    border-color: #fecaca;
  }
  .recon-badge.over {
    background: rgba(234, 88, 12, 0.1);
    color: #9a3412;
    border-color: #fed7aa;
  }
  .recon-badge.active {
    background: rgba(59, 130, 246, 0.1);
    color: #1e40af;
    border-color: #bfdbfe;
  }
  .recon-badge.unknown {
    background: var(--background, #f9fafb);
    color: var(--text-light, #6b7280);
    border-color: var(--border, #e5e7eb);
  }

  /* Open modal */
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
    max-width: 420px;
    width: 100%;
    max-height: 90vh;
    overflow-y: auto;
  }
  .modal h3 {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0;
    margin-bottom: 1rem;
    font-size: 1.05rem;
    color: var(--text, #111827);
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
    background: var(--surface, #fff);
    color: var(--text, #111827);
    font-size: 0.9rem;
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
    gap: 0.5rem;
    margin-top: 1rem;
  }

  @media (max-width: 640px) {
    .drawer-strip {
      grid-template-columns: repeat(2, 1fr);
      row-gap: 0.6rem;
    }
    .detail-row {
      flex-direction: column;
      align-items: flex-start;
      gap: 0.2rem;
    }
    .detail-row strong {
      text-align: left;
    }
    .session-row {
      flex-direction: column;
      align-items: stretch;
    }
    .sr-right {
      justify-content: space-between;
    }
    .card {
      padding: 1rem;
    }
  }
</style>