<script>
  import { login } from "../stores/auth.js";
  import { Mail, Lock, Eye, EyeOff, AlertCircle } from "lucide-svelte";

  let email = "";
  let password = "";
  let showPassword = false;
  let loading = false;
  let error = "";

  async function handleSubmit() {
    if (!email || !password) {
      error = "Email and password are required";
      return;
    }
    loading = true;
    error = "";
    try {
      await login(email, password);
      if (window.navigate) {
        window.navigate("/");
      } else {
        window.location.href = "/";
      }
    } catch (err) {
      error = err.response?.data?.detail || "Invalid email or password";
    } finally {
      loading = false;
    }
  }

  function goToRegister() {
    window.location.href = "/register";
  }
</script>

<div class="auth-container">
  <div class="auth-card">
    <div class="logo-section">
      <img src="/logo-192.png" alt="PHINDU Logo" class="logo-img" />
      <h1>Welcome Back</h1>
      <p class="subtitle">Sign in to continue to your dashboard</p>
    </div>

    <form on:submit|preventDefault={handleSubmit}>
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

      {#if error}
        <div class="error-message">
          <AlertCircle size={16} strokeWidth={2} />
          <span>{error}</span>
        </div>
      {/if}

      <button type="submit" class="btn-primary" disabled={loading}>
        {#if loading}
          <span class="spinner"></span> Signing in...
        {:else}
          Sign In
        {/if}
      </button>

      <div class="divider">
        <span>New to PHINDU?</span>
      </div>

      <button type="button" class="btn-secondary" on:click={goToRegister}>
        Create an Account
      </button>
    </form>

    <p class="footer-text">Small Businesses Sales &amp; Insights</p>
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
    padding: clamp(1.1rem, 3.5vw, 2.25rem);
    width: 100%;
    max-width: 420px;
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
    margin-bottom: clamp(0.9rem, 2.5vh, 1.6rem);
  }

  .logo-img {
    height: clamp(48px, 8vh, 72px);
    width: clamp(48px, 8vh, 72px);
    object-fit: contain;
    margin-bottom: 0.6rem;
  }

  h1 {
    font-size: clamp(1.25rem, 4vw, 1.55rem);
    font-weight: 700;
    color: #0f172a;
    margin: 0 0 0.3rem;
  }

  .subtitle {
    color: #64748b;
    font-size: clamp(0.78rem, 2.5vw, 0.9rem);
    margin: 0;
  }

  .form-group {
    margin-bottom: clamp(0.7rem, 2vh, 1.1rem);
  }

  label {
    display: block;
    margin-bottom: 0.35rem;
    font-weight: 600;
    color: #334155;
    font-size: clamp(0.78rem, 2.4vw, 0.88rem);
  }

  .input-icon {
    position: relative;
    display: flex;
    align-items: center;
  }

  .input-icon :global(.icon) {
    position: absolute;
    left: 0.9rem;
    color: #94a3b8;
    pointer-events: none;
  }

  .input-icon input {
    width: 100%;
    padding: clamp(0.6rem, 2vh, 0.85rem) 2.6rem;
    border: 1.5px solid #e2e8f0;
    border-radius: 11px;
    font-size: clamp(0.85rem, 2.6vw, 0.95rem);
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
    right: 0.7rem;
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.25rem;
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
    padding: 0.55rem 0.75rem;
    border-radius: 9px;
    margin-bottom: 0.7rem;
    font-size: clamp(0.75rem, 2.3vw, 0.85rem);
  }

  .btn-primary {
    width: 100%;
    padding: clamp(0.65rem, 2vh, 0.85rem);
    background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%);
    color: white;
    border: none;
    border-radius: 11px;
    font-size: clamp(0.88rem, 2.6vw, 1rem);
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
    padding: clamp(0.6rem, 1.9vh, 0.8rem);
    background: transparent;
    color: #4f46e5;
    border: 1.5px solid #c7d2fe;
    border-radius: 11px;
    font-size: clamp(0.85rem, 2.5vw, 0.95rem);
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
    margin: clamp(0.7rem, 2vh, 1.1rem) 0;
    color: #94a3b8;
    font-size: clamp(0.72rem, 2.2vw, 0.8rem);
  }

  .divider::before,
  .divider::after {
    content: "";
    flex: 1;
    border-bottom: 1px solid #e2e8f0;
  }

  .divider span {
    margin: 0 0.8rem;
  }

  .footer-text {
    text-align: center;
    margin: clamp(0.7rem, 2vh, 1.1rem) 0 0;
    color: #94a3b8;
    font-size: clamp(0.68rem, 2vw, 0.75rem);
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

  /* Very short viewports: hide subtitle/footer to keep everything on-screen */
  @media (max-height: 560px) {
    .subtitle {
      display: none;
    }
    .logo-section {
      margin-bottom: 0.6rem;
    }
    .divider {
      margin: 0.55rem 0;
    }
    .footer-text {
      display: none;
    }
  }
</style>
