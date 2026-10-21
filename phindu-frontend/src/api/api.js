import axios from "axios";

// 🔧 TEMPORARY: hardcoded to localhost for development
// TODO Sprint 4: restore env-based URL and delete this hardcode
const API = axios.create({
  baseURL: "http://localhost:8000",
  headers: {
    "Content-Type": "application/json"
  }
});

// Global error handler
API.interceptors.response.use(
  res => res,
  err => {
    console.error("API ERROR:", err.response?.data || err.message);
    return Promise.reject(err);
  }
);

export default API;