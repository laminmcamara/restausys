import React, { useState, useEffect } from "react";
import { AuthContext } from "./auth-context";

const API_BASE = "http://127.0.0.1:8000";

export function AuthProvider({ children }) {
  const [accessToken, setAccessToken] = useState(() =>
    localStorage.getItem("accessToken")
  );

  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  const logout = () => {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");

    setAccessToken(null);
    setUser(null);
    setAuthLoading(false);
  };

  const fetchUser = async (token) => {
    try {
      const response = await fetch(`${API_BASE}/api/me/`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        logout();
        return null;
      }

      const data = await response.json();
      setUser(data);

      return data;
    } catch (err) {
      logout();
      return null;
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      const storedAccessToken = localStorage.getItem("accessToken");

      if (!storedAccessToken) {
        setAuthLoading(false);
        return;
      }

      setAccessToken(storedAccessToken);
      await fetchUser(storedAccessToken);
      setAuthLoading(false);
    };

    initAuth();
  }, []);

  const login = async (username, password) => {
    setAuthLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/token/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username,
          password,
        }),
      });

      if (!response.ok) {
        setAuthLoading(false);
        return false;
      }

      const data = await response.json();

      localStorage.setItem("accessToken", data.access);
      localStorage.setItem("refreshToken", data.refresh);

      setAccessToken(data.access);

      await fetchUser(data.access);

      setAuthLoading(false);

      return true;
    } catch (err) {
      console.error("Login error:", err);
      setAuthLoading(false);
      return false;
    }
  };

  // New function to fetch with authorization
  const authFetch = async (url, options = {}) => {
    const headers = {
      ...options.headers,
      Authorization: `Bearer ${accessToken}`, // Include the access token
    };

    const response = await fetch(url, {
      ...options,
      headers,
    });

    return response;
  };

  // New function to parse error messages
  const parseError = async (response, defaultMessage) => {
    const errorData = await response.json();
    return errorData.message || defaultMessage;
  };

  return (
    <AuthContext.Provider
      value={{
        accessToken,
        user,
        authLoading,
        isAuthenticated: Boolean(accessToken),
        login,
        logout,
        authFetch, // Exporting authFetch
        parseError, // Exporting parseError
      }}>
      {children}
    </AuthContext.Provider>
  );
}
