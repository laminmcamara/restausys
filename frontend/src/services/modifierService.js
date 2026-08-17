// modifierService.js
import { useAuth } from "../hooks/useAuth"; // Import the custom hook

const API = "http://127.0.0.1:8000/api/v1/manager";

export const createModifierOption = async (payload, accessToken) => {
    const res = await authFetch(`${API}/modifier-options/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${accessToken}`,
        },
        body: JSON.stringify(payload),
    });

    if (!res) {
        throw new Error("No response from server");
    }

    if (!res.ok) {
        throw new Error(await parseError(res, "Failed to create modifier option"));
    }

    return res.json();
};

export const updateModifierOption = async (id, payload, accessToken) => {
    const res = await authFetch(`${API}/modifier-options/${id}/`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${accessToken}`,
        },
        body: JSON.stringify(payload),
    });

    if (!res) {
        throw new Error("No response from server");
    }

    if (!res.ok) {
        throw new Error(await parseError(res, "Failed to update modifier option"));
    }

    return res.json();
};

export const deleteModifierOption = async (id, accessToken) => {
    const res = await authFetch(`${API}/modifier-options/${id}/`, {
        method: "DELETE",
        headers: {
            "Authorization": `Bearer ${accessToken}`,
        },
    });

    if (!res) {
        throw new Error("No response from server");
    }

    if (!res.ok) {
        throw new Error(await parseError(res, "Failed to delete modifier option"));
    }

    return res.status === 204 ? null : res.json().catch(() => null);
};

export const fetchModifierGroups = async (accessToken) => {
    const res = await authFetch(`${API}/modifier-groups/`, {
        method: "GET",
        headers: {
            "Authorization": `Bearer ${accessToken}`,
        },
    });

    if (!res) {
        throw new Error("No response from server");
    }

    if (!res.ok) {
        throw new Error(await parseError(res, "Failed to fetch modifier groups"));
    }

    return res.json();
};

// New function to delete a modifier group
export const deleteModifierGroup = async (id, accessToken) => {
    const res = await authFetch(`${API}/modifier-groups/${id}/`, {
        method: "DELETE",
        headers: {
            "Authorization": `Bearer ${accessToken}`,
        },
    });

    if (!res) {
        throw new Error("No response from server");
    }

    if (!res.ok) {
        throw new Error(await parseError(res, "Failed to delete modifier group"));
    }

    return res.status === 204 ? null : res.json().catch(() => null);
};
