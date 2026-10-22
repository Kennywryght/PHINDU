import axios from "axios";

// Use VITE_API_URL in production (Vercel/Render/Netlify),
// fall back to localhost for local dev.
const baseURL =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.DEV ? "http://localhost:8000" : "https://phindu-backend-1.onrender.com");

const API = axios.create({
  baseURL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Global error handler
API.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error("API ERROR:", err.response?.data || err.message);
    return Promise.reject(err);
  }
);

export default API;
