import React, { useEffect, useState } from "react";
import ModifierGroupForm from "../components/modifiers/ModifierGroupForm";
import ModifierGroupList from "../components/modifiers/ModifierGroupList";
import api from "../services/api";

const ModifierGroups = () => {
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadGroups = async () => {
    setLoading(true);
    setError("");
    try {
      // FIXED: Using centralized API service
      // Handles baseURL and Authorization automatically
      const res = await api.get("/manager/modifier-groups/");

      // Handle both direct array and paginated results
      const data = res.data.results || res.data;
      setGroups(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Failed to load modifier groups:", err);
      setError("Could not load modifier groups. Please check your connection.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGroups();
  }, []);

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Modifier Groups</h1>
          <p className="text-gray-500 mt-1">
            Create groups like "Size" or "Extra Toppings" to customize your
            products.
          </p>
        </div>

        <button
          onClick={loadGroups}
          className="text-sm text-blue-600 hover:text-blue-800 font-medium">
          Refresh List
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Form */}
        <div className="lg:col-span-1">
          <ModifierGroupForm onSuccess={loadGroups} />
        </div>

        {/* Right Column: List */}
        <div className="lg:col-span-2">
          {loading ? (
            <div className="flex items-center justify-center p-12 bg-white border rounded-xl border-dashed">
              <div className="text-gray-400 animate-pulse">
                Loading groups...
              </div>
            </div>
          ) : (
            <ModifierGroupList
              groups={groups}
              onRefresh={loadGroups}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default ModifierGroups;
