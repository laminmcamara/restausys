// frontend/src/services/api.js
import axios from "axios";

const BASE_URL = "http://127.0.0.1:8000/api";

const api = axios.create({
  baseURL: BASE_URL,
});

/* ================= REQUEST INTERCEPTOR ================= */

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("accessToken");

    console.log("API REQUEST:", {
      url: `${config.baseURL || ""}${config.url || ""}`,
      method: config.method,
      hasToken: Boolean(token),
    });

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

/* ================= RESPONSE INTERCEPTOR ================= */

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    console.error("API ERROR:", {
      url: `${originalRequest?.baseURL || ""}${originalRequest?.url || ""}`,
      status: error.response?.status,
      data: error.response?.data,
    });

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = localStorage.getItem("refreshToken");

      if (!refreshToken) {
        localStorage.clear();
        window.location.href = "/";
        return Promise.reject(error);
      }

      try {
        const response = await axios.post(`${BASE_URL}/token/refresh/`, {
          refresh: refreshToken,
        });

        const newAccess = response.data.access;

        localStorage.setItem("accessToken", newAccess);

        originalRequest.headers = originalRequest.headers || {};
        originalRequest.headers.Authorization = `Bearer ${newAccess}`;

        return api(originalRequest);
      } catch (refreshError) {
        console.error(
          "TOKEN REFRESH FAILED:",
          refreshError.response?.data || refreshError.message
        );

        localStorage.clear();
        window.location.href = "/";
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default api;