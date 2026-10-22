import { writable } from "svelte/store";
import API from "../api/api";

// Stores
export const user = writable(null);
export const token = writable(localStorage.getItem("token") || null);

// Initialize Axios header if token exists
if (typeof window !== "undefined") {
  const storedToken = localStorage.getItem("token");
  if (storedToken) {
    API.defaults.headers.common["Authorization"] = `Bearer ${storedToken}`;
  }
}

// Fetch current user profile
export async function fetchUser() {
  try {
    const res = await API.get("/auth/me");
    user.set(res.data);
    return res.data;
  } catch (err) {
    console.error("Failed to fetch user", err);
    logout();
    return null;
  }
}

// Login
export async function login(email, password) {
  const formData = new FormData();
  formData.append("username", email);
  formData.append("password", password);

  const res = await API.post("/auth/login", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  const { access_token } = res.data;

  localStorage.setItem("token", access_token);
  API.defaults.headers.common["Authorization"] = `Bearer ${access_token}`;
  token.set(access_token);

  await fetchUser();
  return true;
}

// Register
export async function register(shopName, fullName, email, password) {
  const res = await API.post("/auth/register", {
    shop_name: shopName,
    full_name: fullName,
    email,
    password,
  });
  const { access_token } = res.data;

  localStorage.setItem("token", access_token);
  API.defaults.headers.common["Authorization"] = `Bearer ${access_token}`;
  token.set(access_token);

  await fetchUser();
  return true;
}

// Logout
export function logout() {
  localStorage.removeItem("token");
  delete API.defaults.headers.common["Authorization"];
  token.set(null);
  user.set(null);
}

// Auto-fetch user if token exists (call this in App.svelte onMount)
if (typeof window !== "undefined" && localStorage.getItem("token")) {
  fetchUser();
}