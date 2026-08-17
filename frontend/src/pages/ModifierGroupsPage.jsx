import React, { useEffect, useState } from "react";
import ModifierGroupForm from "../components/modifiers/ModifierGroupForm";
import ModifierGroupList from "../components/modifiers/ModifierGroupList";
import { fetchModifierGroups } from "../services/modifierService";
import { useAuth } from "../hooks/useAuth";



const ModifierGroups = () => {
  const { accessToken, refreshAccessToken, logout } = useAuth();

  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadGroups = async () => {
    if (!accessToken) return;

    setLoading(true);

    try {
      const data = await fetchModifierGroups(
        accessToken,
        refreshAccessToken,
        logout
      );

      setGroups(Array.isArray(data) ? data : data.results || []);
    } catch (err) {
      console.error("Failed to load modifier groups:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGroups();
  }, [accessToken]);

  if (loading) return <p>Loading modifier groups...</p>;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold mb-6">Modifier Groups</h1>

      <ModifierGroupForm
        token={accessToken}
        onSuccess={loadGroups}
      />

      <ModifierGroupList
        groups={groups}
        token={accessToken}
        onRefresh={loadGroups}
      />
    </div>
  );
};

export default ModifierGroups;
