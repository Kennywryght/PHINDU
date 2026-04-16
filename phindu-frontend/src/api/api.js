import axios from "axios";

const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "https://phindu-backend-1.onrender.com/",
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

export default API;   // <-- THIS LINE IS CRITICAL