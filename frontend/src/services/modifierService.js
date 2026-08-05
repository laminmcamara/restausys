const API = "http://127.0.0.1:8000/api/v1/manager";

const parseError = async (res, fallbackMessage) => {
  const data = await res.json().catch(() => null);

  if (data?.detail) return data.detail;
  if (data?.error) return data.error;

  if (typeof data === "object" && data !== null) {
    const firstKey = Object.keys(data)[0];

    if (firstKey) {
      const value = data[firstKey];

      if (Array.isArray(value)) {
        return `${firstKey}: ${value.join(", ")}`;
      }

      return `${firstKey}: ${value}`;
    }
  }

  return fallbackMessage;
};

const authFetch = async (url, options = {}, accessToken) => {
  return fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
  });
};

export const fetchModifierGroups = async (accessToken) => {
  const res = await authFetch(`${API}/modifier-groups/`, {}, accessToken);

  if (!res) return [];

  if (!res.ok) {
    throw new Error(await parseError(res, "Failed to fetch modifier groups"));
  }

  return res.json();
};