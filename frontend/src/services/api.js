// frontend/src/services/api.js
import axios from "axios";

const BASE_URL = "http://127.0.0.1:8000/api/v1";

const api = axios.create({
  baseURL: BASE_URL,
});

const refreshClient = axios.create({
  baseURL: BASE_URL,
});

let refreshPromise = null;

function getAccessToken() {
  return localStorage.getItem("accessToken");
}

function getRefreshToken() {
  return localStorage.getItem("refreshToken");
}

function saveTokens(data) {
  if (data.access) {
    localStorage.setItem("accessToken", data.access);
  }

  // Required when ROTATE_REFRESH_TOKENS is enabled
  if (data.refresh) {
    localStorage.setItem("refreshToken", data.refresh);
  }
}

function logout() {
  localStorage.removeItem("accessToken");
  localStorage.removeItem("refreshToken");
  window.location.href = "/";
}

/* ================= REQUEST INTERCEPTOR ================= */

api.interceptors.request.use(
  (config) => {
    const token = getAccessToken();

    config.headers = config.headers || {};

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
    const status = error.response?.status;

    if (
      status !== 401 ||
      !originalRequest ||
      originalRequest._retry ||
      originalRequest.url?.includes("/token/refresh/")
    ) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    const refreshToken = getRefreshToken();

    if (!refreshToken) {
      logout();
      return Promise.reject(error);
    }

    try {
      // Reuse one refresh request if several API requests fail together
      if (!refreshPromise) {
        refreshPromise = refreshClient
          .post("/token/refresh/", {
            refresh: refreshToken,
          })
          .then((response) => {
            saveTokens(response.data);
            return response.data.access;
          })
          .finally(() => {
            refreshPromise = null;
          });
      }

      const newAccessToken = await refreshPromise;

      originalRequest.headers = originalRequest.headers || {};
      originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;

      return api(originalRequest);
    } catch (refreshError) {
      console.error(
        "TOKEN REFRESH FAILED:",
        refreshError.response?.data || refreshError.message
      );

      logout();
      return Promise.reject(refreshError);
    }
  }
);

export default api;