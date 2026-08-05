import React, { useEffect, useState } from "react";
import ModifierGroupForm from "../components/modifiers/ModifierGroupForm";
import ModifierGroupList from "../components/modifiers/ModifierGroupList";
import { fetchModifierGroups } from "../services/modifierService";

const ModifierGroupsPage = () => {
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const token = localStorage.getItem("access");

  const loadGroups = async () => {
    try {
      const data = await fetchModifierGroups(
        accessToken,
        refreshAccessToken,
        logout
      );
      
      setGroups(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGroups();
  }, []);

  if (loading) return <p>Loading modifier groups...</p>;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold mb-6">Modifier Groups</h1>

      <ModifierGroupForm
        token={token}
        onSuccess={loadGroups}
      />

      <ModifierGroupList
        groups={groups}
        token={token}
        onRefresh={loadGroups}
      />
    </div>
  );
};

export default ModifierGroupsPage;
