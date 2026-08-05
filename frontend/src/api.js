export async function apiFetch(
  url,
  options = {},
  accessToken,
  refreshAccessToken,
  logout
) {
  let token = accessToken;

  let res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  if (res.status === 401 && refreshAccessToken) {
    try {
      const newToken = await refreshAccessToken();

      if (!newToken) {
        if (logout) logout();
        return res;
      }

      token = newToken;

      res = await fetch(url, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...(options.headers || {}),
          Authorization: `Bearer ${token}`,
        },
      });
    } catch (err) {
      console.error("Token refresh failed:", err);
      if (logout) logout();
      return res;
    }
  }

  return res;
}