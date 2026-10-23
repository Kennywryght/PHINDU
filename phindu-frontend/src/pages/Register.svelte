<script>
  import { register } from "../stores/auth.js";
  import { Store, User, Mail, Lock, Check, Eye, EyeOff, AlertCircle } from "lucide-svelte";

  let shopName = "";
  let fullName = "";
  let email = "";
  let password = "";
  let confirmPassword = "";
  let showPassword = false;
  let showConfirmPassword = false;
  let loading = false;
  let error = "";

  async function handleSubmit() {
    if (!shopName || !fullName || !email || !password) {
      error = "All fields are required";
      return;
    }
    if (password !== confirmPassword) {
      error = "Passwords do not match";
      return;
    }
    if (password.length < 4) {
      error = "Password must be at least 4 characters";
      return;
    }
    loading = true;
    error = "";
    try {
      await register(shopName, fullName, email, password);
      if (window.navigate) {
        window.navigate("/");
      } else {
        window.location.href = "/";
      }
    } catch (err) {
      error = err.response?.data?.detail || "Registration failed. Please try again.";
    } finally {
      loading = false;
    }
  }

  function goToLogin() {
    window.location.href = "/login";
  }
</script>

<div class="auth-container">
  <div class="auth-card">
    <div class="logo-section">
      <img src="/logo-192.png" alt="PHINDU Logo" class="logo-img" />
      <h1>Create Your Shop</h1>
      <p class="subtitle">Start managing your business in minutes</p>
    </div>

    <form on:submit|preventDefault={handleSubmit}>
      <div class="form-group">
        <label for="shopName">Shop Name</label>
        <div class="input-icon">
          <Store size={18} strokeWidth={1.75} class="icon" />
          <input
            id="shopName"
            type="text"
            bind:value={shopName}
            placeholder="e.g., My Grocery Store"
            required
            disabled={loading}
          />
        </div>
      </div>

      <div class="form-group">
        <label for="fullName">Your Full Name</label>
        <div class="input-icon">
          <User size={18} strokeWidth={1.75} class="icon" />
          <input
            id="fullName"
            type="text"
            bind:value={fullName}
            placeholder="e.g., John Banda"
            required
            disabled={loading}
          />
        </div>
      </div>

      <div class="form-group">
        <label for="email">Email Address</label>
        <div class="input-icon">
          <Mail size={18} strokeWidth={1.75} class="icon" />
          <input
            id="email"
            type="email"
            bind:value={email}
            placeholder="you@example.com"
            required
            disabled={loading}
          />
        </div>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label for="password">Password</label>
          <div class="input-icon">
            <Lock size={18} strokeWidth={1.75} class="icon" />
            <input
              id="password"
              type={showPassword ? "text" : "password"}
              bind:value={password}
              placeholder="••••••••"
              required
              disabled={loading}
            />
            <button
              type="button"
              class="toggle-password"
              on:click={() => (showPassword = !showPassword)}
              tabindex="-1"
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {#if showPassword}
                <EyeOff size={18} strokeWidth={1.75} />
              {:else}
                <Eye size={18} strokeWidth={1.75} />
              {/if}
            </button>
          </div>
        </div>

        <div class="form-group">
          <label for="confirmPassword">Confirm</label>
          <div class="input-icon">
            <Check size={18} strokeWidth={2} class="icon" />
            <input
              id="confirmPassword"
              type={showConfirmPassword ? "text" : "password"}
              bind:value={confirmPassword}
              placeholder="••••••••"
              required
              disabled={loading}
            />
            <button
              type="button"
              class="toggle-password"
              on:click={() => (showConfirmPassword = !showConfirmPassword)}
              tabindex="-1"
              aria-label={showConfirmPassword ? "Hide password" : "Show password"}
            >
              {#if showConfirmPassword}
                <EyeOff size={18} strokeWidth={1.75} />
              {:else}
                <Eye size={18} strokeWidth={1.75} />
              {/if}
            </button>
          </div>
        </div>
      </div>

      {#if error}
        <div class="error-message">
          <AlertCircle size={16} strokeWidth={2} />
          <span>{error}</span>
        </div>
      {/if}

      <button type="submit" class="btn-primary" disabled={loading}>
        {#if loading}
          <span class="spinner"></span> Creating account...
        {:else}
          Create Shop &amp; Continue
        {/if}
      </button>

      <div class="divider">
        <span>Already have an account?</span>
      </div>

      <button type="button" class="btn-secondary" on:click={goToLogin}>Sign In</button>
    </form>

    <p class="footer-text">By creating an account, you agree to our Terms of Service</p>
  </div>
</div>

<style>
  /* NOTE: no :global(html)/:global(body) rules here — those used to kill
     scrolling on every page of the app. The auth screen is pinned to the
     viewport via position:fixed on .auth-container instead. */

  .auth-container {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background:
      radial-gradient(circle at 20% 20%, #312e81 0%, transparent 45%),
      radial-gradient(circle at 80% 80%, #0f766e 0%, transparent 45%),
      linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    padding: clamp(0.5rem, 3vw, 2rem);
    box-sizing: border-box;
    overflow: hidden;
  }

  .auth-card {
    background: #ffffff;
    border-radius: 20px;
    box-shadow: 0 25px 60px -15px rgba(2, 6, 23, 0.6);
    padding: clamp(1rem, 3vw, 2rem);
    width: 100%;
    max-width: 480px;
    max-height: calc(100dvh - 1.5rem);
    overflow-y: auto;
    box-sizing: border-box;
    animation: slideUp 0.35s ease-out;
  }

  @keyframes slideUp {
    from {
      opacity: 0;
      transform: translateY(14px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .logo-section {
    text-align: center;
    margin-bottom: clamp(0.7rem, 2vh, 1.2rem);
  }

  .logo-img {
    height: clamp(44px, 7vh, 64px);
    width: clamp(44px, 7vh, 64px);
    object-fit: contain;
    margin-bottom: 0.5rem;
  }

  h1 {
    font-size: clamp(1.15rem, 3.6vw, 1.45rem);
    font-weight: 700;
    color: #0f172a;
    margin: 0 0 0.25rem;
  }

  .subtitle {
    color: #64748b;
    font-size: clamp(0.75rem, 2.3vw, 0.85rem);
    margin: 0;
  }

  .form-group {
    margin-bottom: clamp(0.55rem, 1.6vh, 0.95rem);
  }

  .form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.6rem;
  }

  label {
    display: block;
    margin-bottom: 0.3rem;
    font-weight: 600;
    color: #334155;
    font-size: clamp(0.75rem, 2.3vw, 0.85rem);
  }

  .input-icon {
    position: relative;
    display: flex;
    align-items: center;
  }

  .input-icon :global(.icon) {
    position: absolute;
    left: 0.85rem;
    color: #94a3b8;
    pointer-events: none;
  }

  .input-icon input {
    width: 100%;
    padding: clamp(0.55rem, 1.8vh, 0.8rem) 2.4rem;
    border: 1.5px solid #e2e8f0;
    border-radius: 11px;
    font-size: clamp(0.82rem, 2.5vw, 0.92rem);
    transition: all 0.18s;
    background: #f8fafc;
    color: #0f172a;
    box-sizing: border-box;
  }

  .input-icon input:focus {
    outline: none;
    background: #ffffff;
    border-color: #4f46e5;
    box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15);
  }

  .input-icon input::placeholder {
    color: #cbd5e1;
  }

  .toggle-password {
    position: absolute;
    right: 0.6rem;
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.2rem;
    color: #64748b;
    line-height: 0;
    border-radius: 6px;
    transition: color 0.15s;
  }

  .toggle-password:hover {
    color: #4f46e5;
  }

  .error-message {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    background: #fef2f2;
    color: #b91c1c;
    border: 1px solid #fecaca;
    padding: 0.5rem 0.7rem;
    border-radius: 9px;
    margin-bottom: 0.65rem;
    font-size: clamp(0.72rem, 2.2vw, 0.82rem);
  }

  .btn-primary {
    width: 100%;
    padding: clamp(0.6rem, 1.9vh, 0.8rem);
    background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%);
    color: white;
    border: none;
    border-radius: 11px;
    font-size: clamp(0.85rem, 2.5vw, 0.98rem);
    font-weight: 600;
    cursor: pointer;
    transition: filter 0.18s, transform 0.1s;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    box-shadow: 0 6px 16px -4px rgba(79, 70, 229, 0.5);
  }

  .btn-primary:hover:not(:disabled) {
    filter: brightness(1.07);
  }
  .btn-primary:active:not(:disabled) {
    transform: translateY(1px);
  }
  .btn-primary:disabled {
    opacity: 0.65;
    cursor: not-allowed;
  }

  .btn-secondary {
    width: 100%;
    padding: clamp(0.55rem, 1.8vh, 0.75rem);
    background: transparent;
    color: #4f46e5;
    border: 1.5px solid #c7d2fe;
    border-radius: 11px;
    font-size: clamp(0.82rem, 2.4vw, 0.92rem);
    font-weight: 600;
    cursor: pointer;
    transition: all 0.18s;
  }

  .btn-secondary:hover {
    background: #eef2ff;
    border-color: #4f46e5;
  }

  .divider {
    display: flex;
    align-items: center;
    text-align: center;
    margin: clamp(0.55rem, 1.6vh, 0.95rem) 0;
    color: #94a3b8;
    font-size: clamp(0.7rem, 2.1vw, 0.78rem);
  }

  .divider::before,
  .divider::after {
    content: "";
    flex: 1;
    border-bottom: 1px solid #e2e8f0;
  }

  .divider span {
    margin: 0 0.75rem;
  }

  .footer-text {
    text-align: center;
    margin: clamp(0.55rem, 1.6vh, 0.95rem) 0 0;
    color: #94a3b8;
    font-size: clamp(0.65rem, 1.9vw, 0.73rem);
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
    to {
      transform: rotate(360deg);
    }
  }

  /* Narrow phones: stack the two password inputs */
  @media (max-width: 420px) {
    .form-row {
      grid-template-columns: 1fr;
      gap: 0;
    }
  }

  /* Very short viewports: hide subtitle/footer so the card fits on-screen */
  @media (max-height: 620px) {
    .subtitle {
      display: none;
    }
    .logo-section {
      margin-bottom: 0.5rem;
    }
    .footer-text {
      display: none;
    }
  }
</style>
