<script>
  import { login } from '../stores/auth.js';
  import { Mail, Lock, Eye, EyeOff, AlertCircle } from 'lucide-svelte';

  let email = '';
  let password = '';
  let showPassword = false;
  let loading = false;
  let error = '';

  async function handleSubmit() {
    if (!email || !password) {
      error = 'Email and password are required';
      return;
    }
    loading = true;
    error = '';
    try {
      await login(email, password);
      if (window.navigate) {
        window.navigate('/');
      } else {
        window.location.href = '/';
      }
    } catch (err) {
      error = err.response?.data?.detail || 'Invalid email or password';
    } finally {
      loading = false;
    }
  }

  function goToRegister() {
    window.location.href = '/register';
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
            type={showPassword ? 'text' : 'password'}
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
            aria-label={showPassword ? 'Hide password' : 'Show password'}
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
  .auth-container {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #0f6b3e 0%, #0a4f2e 100%);
    padding: 1.5rem;
    position: relative;
    overflow: hidden;
  }

  .auth-container::before,
  .auth-container::after {
    content: '';
    position: absolute;
    width: 300px;
    height: 300px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.1);
    pointer-events: none;
  }

  .auth-container::before {
    top: -100px;
    left: -100px;
  }

  .auth-container::after {
    bottom: -100px;
    right: -100px;
    width: 400px;
    height: 400px;
  }

  .auth-card {
    background: white;
    border-radius: 24px;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
    padding: 2.5rem;
    width: 100%;
    max-width: 420px;
    position: relative;
    z-index: 10;
    animation: slideUp 0.4s ease-out;
    box-sizing: border-box;
  }

  @keyframes slideUp {
    from {
      opacity: 0;
      transform: translateY(20px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .logo-section {
    text-align: center;
    margin-bottom: 2rem;
  }

  .logo-img {
    height: 80px;
    width: auto;
    margin-bottom: 1rem;
  }

  h1 {
    font-size: 1.6rem;
    font-weight: 700;
    color: #f59e0b;
    margin: 0 0 0.5rem;
  }

  .subtitle {
    color: #f59e0b;
    font-size: 0.9rem;
    margin: 0;
  }

  .form-group {
    margin-bottom: 1.25rem;
  }

  label {
    display: block;
    margin-bottom: 0.45rem;
    font-weight: 500;
    color: #f59e0b;
    font-size: 0.9rem;
  }

  .input-icon {
    position: relative;
    display: flex;
    align-items: center;
  }

  .input-icon :global(.icon),
  .icon {
    position: absolute;
    left: 1rem;
    color: #94a3b8;
    pointer-events: none;
  }

  .input-icon input {
    width: 100%;
    padding: 0.85rem 1rem 0.85rem 2.75rem;
    border: 1.5px solid #e2e8f0;
    border-radius: 12px;
    font-size: 0.95rem;
    transition: all 0.2s;
    background: white;
    color: #111827;
    box-sizing: border-box;
  }

  .input-icon input:focus {
    outline: none;
    border-color: #0f6b3e;
    box-shadow: 0 0 0 3px rgba(15, 107, 62, 0.1);
  }

  .input-icon input::placeholder {
    color: #cbd5e1;
  }

  .toggle-password {
    position: absolute;
    right: 0.85rem;
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
    color: #f59e0b;
  }

  .error-message {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: #fee2e2;
    color: #991b1b;
    padding: 0.7rem 0.9rem;
    border-radius: 10px;
    margin-bottom: 1.25rem;
    font-size: 0.88rem;
  }

  .btn-primary {
    width: 100%;
    padding: 0.85rem;
    background: #0f6b3e;
    color: white;
    border: none;
    border-radius: 12px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
  }

  .btn-primary:hover:not(:disabled) {
    background: #0a4f2e;
  }

  .btn-primary:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }

  .btn-secondary {
    width: 100%;
    padding: 0.85rem;
    background: white;
    color: #f59e0b;
    border: 1.5px solid #f59e0b;
    border-radius: 12px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-secondary:hover {
    background: #fef3c7;
  }

  .divider {
    display: flex;
    align-items: center;
    text-align: center;
    margin: 1.25rem 0;
    color: #f59e0b;
    font-size: 0.82rem;
  }

  .divider::before,
  .divider::after {
    content: '';
    flex: 1;
    border-bottom: 1px solid #e2e8f0;
  }

  .divider span {
    margin: 0 1rem;
  }

  .footer-text {
    text-align: center;
    margin-top: 1.5rem;
    color: #f59e0b;
    font-size: 0.78rem;
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

  @media (max-width: 480px) {
    .auth-container {
      padding: 1rem;
    }

    .auth-card {
      padding: 1.5rem 1.25rem;
      border-radius: 20px;
    }

    .logo-img {
      height: 64px;
    }

    h1 {
      font-size: 1.4rem;
    }

    .subtitle {
      font-size: 0.85rem;
    }

    .input-icon input {
      padding: 0.75rem 1rem 0.75rem 2.5rem;
      font-size: 0.9rem;
    }
  }
</style>