import { describe, it, expect, vi, beforeEach } from "vitest";
import { get } from "svelte/store";

// Mock the API module BEFORE importing auth
vi.mock("../src/api/api", () => {
  return {
    default: {
      get: vi.fn(),
      post: vi.fn(),
      defaults: { headers: { common: {} } },
    },
  };
});

import API from "../src/api/api";

// We import auth AFTER mock is set up.
// Using dynamic import inside each test because auth.js has module-level
// side effects (auto-fetch on import if a token exists).
async function loadAuth() {
  vi.resetModules();
  return await import("../src/stores/auth.js");
}

describe("auth store", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    API.defaults.headers.common = {};

    // Default mock for the auto-fetch on import: if a test sets a token
    // in localStorage, auth.js calls /auth/me during import. Without a
    // mocked success response, the catch block calls logout() and clears
    // the token before the test can inspect it.
    API.get.mockResolvedValue({ data: { id: "auto", email: "auto@test.com" } });
  });

  it("initializes token from localStorage", async () => {
    localStorage.setItem("token", "abc123");

    const { token } = await loadAuth();

    expect(get(token)).toBe("abc123");
    expect(API.get).toHaveBeenCalledWith("/auth/me");
  });

  it("initializes token as null when localStorage is empty", async () => {
    const { token } = await loadAuth();
    expect(get(token)).toBe(null);
  });

  it("login() stores token and calls fetchUser", async () => {
    API.post.mockResolvedValueOnce({
      data: { access_token: "new-token-xyz" },
    });
    API.get.mockResolvedValueOnce({
      data: { id: "u1", email: "test@test.com", role: "owner" },
    });

    const { login, token, user } = await loadAuth();
    const result = await login("test@test.com", "pass123");

    expect(result).toBe(true);
    expect(get(token)).toBe("new-token-xyz");
    expect(localStorage.getItem("token")).toBe("new-token-xyz");
    expect(get(user)).toEqual({ id: "u1", email: "test@test.com", role: "owner" });
    expect(API.post).toHaveBeenCalledWith(
      "/auth/login",
      expect.any(FormData),
      expect.objectContaining({
        headers: { "Content-Type": "multipart/form-data" },
      })
    );
  });

  it("login() throws on failure and leaves token unchanged", async () => {
    API.post.mockRejectedValueOnce({
      response: { data: { detail: "Invalid credentials" } },
    });

    const { login, token } = await loadAuth();

    await expect(login("bad@test.com", "wrong")).rejects.toBeDefined();
    expect(get(token)).toBe(null);
    expect(localStorage.getItem("token")).toBe(null);
  });

  it("logout() clears token, user, and Authorization header", async () => {
    API.post.mockResolvedValueOnce({ data: { access_token: "abc" } });
    API.get.mockResolvedValueOnce({ data: { id: "u1" } });

    const { login, logout, token, user } = await loadAuth();
    await login("test@test.com", "pass123");

    expect(get(token)).toBe("abc");
    expect(API.defaults.headers.common["Authorization"]).toBe("Bearer abc");

    logout();

    expect(get(token)).toBe(null);
    expect(get(user)).toBe(null);
    expect(localStorage.getItem("token")).toBe(null);
    expect(API.defaults.headers.common["Authorization"]).toBeUndefined();
  });

  it("register() stores token and fetches user", async () => {
    API.post.mockResolvedValueOnce({
      data: { access_token: "register-token" },
    });
    API.get.mockResolvedValueOnce({
      data: { id: "u2", email: "new@test.com", role: "owner" },
    });

    const { register, token, user } = await loadAuth();
    const result = await register("My Shop", "New User", "new@test.com", "pass1234");

    expect(result).toBe(true);
    expect(get(token)).toBe("register-token");
    expect(get(user)).toEqual({ id: "u2", email: "new@test.com", role: "owner" });
    expect(API.post).toHaveBeenCalledWith("/auth/register", {
      shop_name: "My Shop",
      full_name: "New User",
      email: "new@test.com",
      password: "pass1234",
    });
  });

  it("fetchUser() returns null and logs out on API error", async () => {
    localStorage.setItem("token", "old-token");
    // Every API.get fails — both the auto-fetch on import AND the explicit call
    API.get.mockRejectedValue(new Error("Network error"));

    const { fetchUser, token } = await loadAuth();
    const result = await fetchUser();

    expect(result).toBe(null);
    expect(get(token)).toBe(null);
    expect(localStorage.getItem("token")).toBe(null);
  });
});