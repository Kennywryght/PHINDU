<script>
  import { onMount } from "svelte";
  import {
    User,
    Mail,
    Shield,
    Store,
    Sun,
    Moon,
    Globe,
    LogOut,
    KeyRound,
    Loader2,
    CheckCircle2,
    AlertCircle,
  } from "lucide-svelte";
  import { user as userStore, token as tokenStore, fetchUser, logout } from "../stores/auth";
  import { locale } from "svelte-i18n";
  import Layout from "../components/Layout.svelte";
  import ChangePasswordModal from "../components/ChangePasswordModal.svelte";
  import API from "../api/api";

  let currentUser = null;
  let loading = true;
  let error = null;

  // Editable name
  let fullName = "";
  let savingName = false;
  let nameMsg = "";
  let nameMsgKind = "";

  // Theme / locale
  let theme = typeof window !== "undefined" ? localStorage.getItem("theme") || "light" : "light";
  let currentLocale = typeof window !== "undefined" ? localStorage.getItem("locale") || "en" : "en";

  // Password modal
  let showPasswordModal = false;
  let passwordMsg = "";

  const unsub = userStore.subscribe((u) => {
    currentUser = u;
    if (u && !fullName) fullName = u.full_name || "";
  });

  onMount(async () => {
    try {
      if (!currentUser) await fetchUser();
    } catch (err) {
      error = "Failed to load profile";
    } finally {
      loading = false;
    }
  });

  import { onDestroy } from "svelte";
  onDestroy(unsub);

  function roleLabel(role) {
    if (role === "owner") return "Owner";
    if (role === "manager") return "Manager";
    return "Cashier";
  }

  function initials(name) {
    if (!name) return "?";
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) return parts[0][0].toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }

  async function saveName() {
    nameMsg = "";
    if (!fullName.trim()) {
      nameMsg = "Name cannot be empty";
      nameMsgKind = "error";
      return;
    }
    savingName = true;
    try {
      await API.put("/auth/me", { full_name: fullName.trim() });
      await fetchUser();
      nameMsg = "Name updated";
      nameMsgKind = "success";
      setTimeout(() => (nameMsg = ""), 2500);
    } catch (err) {
      nameMsg = err.response?.data?.detail || "Failed to update name";
      nameMsgKind = "error";
    } finally {
      savingName = false;
    }
  }

  function toggleTheme() {
    theme = theme === "light" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }

  function setLocale(l) {
    currentLocale = l;
    locale.set(l);
    localStorage.setItem("locale", l);
  }

  function handleLogout() {
    if (confirm("Sign out of PHINDU?")) {
      logout();
      window.location.href = "/login";
    }
  }

  function openPasswordModal() {
    passwordMsg = "";
    showPasswordModal = true;
  }
  function closePasswordModal() {
    showPasswordModal = false;
  }
  function onPasswordChanged() {
    showPasswordModal = false;
    passwordMsg = "Password changed successfully";
    setTimeout(() => (passwordMsg = ""), 3000);
  }
</script>

<Layout title="Profile">
  <div class="profile-page">
    {#if loading}
      <div class="loading-row">
        <Loader2 size={20} class="spin" /> Loading profile…
      </div>
    {:else if error}
      <div class="error-box">
        <AlertCircle size={16} /> {error}
      </div>
    {:else if currentUser}
      <!-- Header card -->
      <div class="header-card">
        <div class="avatar">{initials(currentUser.full_name)}</div>
        <div class="header-info">
          <h2>{currentUser.full_name}</h2>
          <p class="header-meta">
            <span>{currentUser.email}</span>
            <span class="role-pill role-{currentUser.role}">
              <Shield size={12} strokeWidth={2} />
              {roleLabel(currentUser.role)}
            </span>
          </p>
          {#if currentUser.shop_name}
            <p class="shop-line">
              <Store size={14} strokeWidth={2} />
              {currentUser.shop_name}
            </p>
          {/if}
        </div>
      </div>

      <!-- Account details -->
      <div class="card">
        <h3><User size={16} /> Account details</h3>
        <div class="form-group">
          <label for="pf-name">Full name</label>
          <input id="pf-name" type="text" bind:value={fullName} disabled={savingName} />
        </div>
        <div class="form-group">
          <label for="pf-email">Email</label>
          <div class="readonly-field">
            <Mail size={14} strokeWidth={2} />
            <span>{currentUser.email}</span>
          </div>
          <p class="hint">Email changes are not supported yet — contact support.</p>
        </div>

        {#if nameMsg}
          <div class="inline-msg {nameMsgKind === 'error' ? 'error' : 'success'}">
            {#if nameMsgKind === "error"}
              <AlertCircle size={14} />
            {:else}
              <CheckCircle2 size={14} />
            {/if}
            {nameMsg}
          </div>
        {/if}

        <div class="form-actions">
          <button
            class="btn btn-primary"
            on:click={saveName}
            disabled={savingName || fullName === currentUser.full_name}
            type="button"
          >
            {#if savingName}
              <Loader2 size={14} class="spin" /> Saving…
            {:else}
              Save changes
            {/if}
          </button>
        </div>
      </div>

      <!-- Security -->
      <div class="card">
        <h3><KeyRound size={16} /> Security</h3>
        <div class="security-row">
          <div>
            <strong>Password</strong>
            <p class="hint">Last changed: not tracked</p>
          </div>
          <button class="btn btn-secondary" on:click={openPasswordModal} type="button">
            Change password
          </button>
        </div>
        {#if passwordMsg}
          <div class="inline-msg success">
            <CheckCircle2 size={14} /> {passwordMsg}
          </div>
        {/if}
      </div>

      <!-- Preferences -->
      <div class="card">
        <h3><Sun size={16} /> Preferences</h3>
        <div class="pref-row">
          <span class="pref-label">Theme</span>
          <div class="pref-toggle-group">
            <button
              type="button"
              class="pref-btn"
              class:active={theme === "light"}
              on:click={() => theme !== "light" && toggleTheme()}
            >
              <Sun size={14} /> Light
            </button>
            <button
              type="button"
              class="pref-btn"
              class:active={theme === "dark"}
              on:click={() => theme !== "dark" && toggleTheme()}
            >
              <Moon size={14} /> Dark
            </button>
          </div>
        </div>
        <div class="pref-row">
          <span class="pref-label">Language</span>
          <div class="pref-toggle-group">
            <button
              type="button"
              class="pref-btn"
              class:active={currentLocale === "en"}
              on:click={() => currentLocale !== "en" && setLocale("en")}
            >
              <Globe size={14} /> English
            </button>
            <button
              type="button"
              class="pref-btn"
              class:active={currentLocale === "ny"}
              on:click={() => currentLocale !== "ny" && setLocale("ny")}
            >
              <Globe size={14} /> Chichewa
            </button>
          </div>
        </div>
      </div>

      <!-- Danger zone -->
      <div class="card danger-card">
        <h3><LogOut size={16} /> Sign out</h3>
        <p class="hint">You'll be returned to the login screen.</p>
        <button class="btn btn-danger" on:click={handleLogout} type="button">
          <LogOut size={14} /> Sign out
        </button>
      </div>
    {:else}
      <div class="error-box">Not signed in.</div>
    {/if}
  </div>

  {#if showPasswordModal}
    <ChangePasswordModal on:saved={onPasswordChanged} on:close={closePasswordModal} />
  {/if}
</Layout>

<style>
  .profile-page {
    max-width: 640px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .loading-row {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 2rem;
    color: var(--text-light, #6b7280);
  }
  .spin {
    animation: spin 1s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  .error-box {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: #fee2e2;
    color: #991b1b;
    padding: 0.75rem 1rem;
    border-radius: 8px;
    font-size: 0.9rem;
  }

  /* Header card */
  .header-card {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1.25rem;
    background: linear-gradient(135deg, rgba(15, 107, 62, 0.06) 0%, var(--surface, #fff) 100%);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 12px;
  }
  .avatar {
    width: 64px;
    height: 64px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--primary, #0f6b3e);
    color: white;
    font-size: 1.5rem;
    font-weight: 700;
    border-radius: 50%;
    letter-spacing: 0.05em;
  }
  .header-info {
    flex: 1;
    min-width: 0;
  }
  .header-info h2 {
    margin: 0 0 0.3rem;
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--text, #111827);
    word-break: break-word;
  }
  .header-meta {
    margin: 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
    font-size: 0.85rem;
    color: var(--text-light, #6b7280);
  }
  .role-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.15rem 0.55rem;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    border: 1px solid;
  }
  .role-owner {
    background: rgba(15, 107, 62, 0.1);
    color: #0f6b3e;
    border-color: #86efac;
  }
  .role-manager {
    background: rgba(59, 130, 246, 0.1);
    color: #1e40af;
    border-color: #bfdbfe;
  }
  .role-cashier {
    background: var(--background, #f9fafb);
    color: var(--text-light, #6b7280);
    border-color: var(--border, #e5e7eb);
  }
  .shop-line {
    margin: 0.4rem 0 0;
    font-size: 0.82rem;
    color: var(--text-light, #6b7280);
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
  }

  /* Card */
  .card {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 12px;
    padding: 1.25rem;
  }
  .card h3 {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin-top: 0;
    margin-bottom: 1rem;
    font-size: 0.95rem;
    font-weight: 600;
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
  .readonly-field {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.6rem;
    background: var(--background, #f9fafb);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    font-size: 0.9rem;
    color: var(--text-light, #6b7280);
  }
  .hint {
    font-size: 0.75rem;
    color: var(--text-light, #6b7280);
    margin: 0.35rem 0 0;
  }
  .form-actions {
    display: flex;
    justify-content: flex-end;
    margin-top: 0.5rem;
  }
  .inline-msg {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.5rem 0.75rem;
    border-radius: 8px;
    font-size: 0.85rem;
    margin-bottom: 0.6rem;
    border: 1px solid;
  }
  .inline-msg.success {
    background: rgba(22, 163, 74, 0.1);
    color: #166534;
    border-color: #86efac;
  }
  .inline-msg.error {
    background: #fee2e2;
    color: #991b1b;
    border-color: #fecaca;
  }

  /* Security row */
  .security-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px dashed var(--border, #e5e7eb);
    margin-bottom: 0.5rem;
  }
  .security-row strong {
    font-size: 0.9rem;
    color: var(--text, #111827);
  }

  /* Preferences */
  .pref-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
    padding: 0.6rem 0;
    border-bottom: 1px dashed var(--border, #e5e7eb);
  }
  .pref-row:last-child {
    border-bottom: none;
  }
  .pref-label {
    font-weight: 500;
    font-size: 0.9rem;
    color: var(--text, #111827);
  }
  .pref-toggle-group {
    display: inline-flex;
    gap: 0.25rem;
    background: var(--background, #f9fafb);
    padding: 0.2rem;
    border-radius: 8px;
    border: 1px solid var(--border, #e5e7eb);
  }
  .pref-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    border: none;
    background: transparent;
    padding: 0.4rem 0.75rem;
    border-radius: 6px;
    font-size: 0.8rem;
    font-weight: 500;
    color: var(--text-light, #6b7280);
    cursor: pointer;
    transition: all 0.15s;
  }
  .pref-btn.active {
    background: var(--surface, #fff);
    color: var(--primary, #0f6b3e);
    font-weight: 600;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
  }

  /* Danger card */
  .danger-card {
    border-color: #fecaca;
    background: rgba(220, 38, 38, 0.03);
  }
  .danger-card h3 {
    color: #991b1b;
  }

  /* Buttons */
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
  .btn:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
  .btn-primary {
    background: var(--primary, #0f6b3e);
    color: white;
  }
  .btn-primary:hover:not(:disabled) {
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
  .btn-danger {
    background: #dc2626;
    color: white;
  }
  .btn-danger:hover {
    background: #b91c1c;
  }

  @media (max-width: 480px) {
    .header-card {
      flex-direction: column;
      text-align: center;
      gap: 0.75rem;
    }
    .avatar {
      width: 56px;
      height: 56px;
      font-size: 1.3rem;
    }
    .header-meta {
      justify-content: center;
    }
    .security-row {
      flex-direction: column;
      align-items: stretch;
      gap: 0.6rem;
    }
    .security-row .btn {
      width: 100%;
      justify-content: center;
    }
    .pref-row {
      flex-direction: column;
      align-items: stretch;
    }
  }
</style>