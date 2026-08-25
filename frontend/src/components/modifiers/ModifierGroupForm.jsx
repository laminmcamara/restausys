import React, { useState } from "react";
import api from "../../services/api";

const ModifierGroupForm = ({ onSuccess }) => {
  const [name, setName] = useState("");
  const [selectionType, setSelectionType] = useState("SINGLE");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!name.trim()) {
      setError("Group name is required.");
      return;
    }

    setSaving(true);
    setError("");

    try {
      // FIXED: Using the centralized API service
      // Path matches the /manager/modifier-groups/ pattern
      await api.post("/manager/modifier-groups/", {
        name: name.trim(),
        selection_type: selectionType,
      });

      setName("");
      setSelectionType("SINGLE");
      if (onSuccess) onSuccess();
    } catch (err) {
      console.error("Create Modifier Group Error:", err);
      setError(err.response?.data?.detail || "Failed to create group.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="mb-6 bg-white p-6 rounded-xl border shadow-sm">
      <h2 className="text-lg font-bold text-gray-800 mb-4">
        Create Modifier Group
      </h2>

      {error && (
        <div className="mb-4 p-2 text-sm text-red-600 bg-red-50 border border-red-100 rounded">
          {error}
        </div>
      )}

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Group Name
          </label>
          <input
            type="text"
            placeholder="e.g. Extra Toppings, Meat Temp, Size"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="w-full border border-gray-300 p-2 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Selection Type
          </label>
          <select
            value={selectionType}
            onChange={(e) => setSelectionType(e.target.value)}
            className="w-full border border-gray-300 p-2 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition">
            <option value="SINGLE">Single Choice (Radio buttons)</option>
            <option value="MULTIPLE">Multiple Choices (Checkboxes)</option>
          </select>
          <p className="mt-1 text-xs text-gray-500">
            {selectionType === "SINGLE"
              ? "Customers can only pick one option from this group."
              : "Customers can select multiple options from this group."}
          </p>
        </div>

        <button
          type="submit"
          disabled={saving}
          className={`w-full py-2 px-4 rounded-lg font-bold text-white transition ${
            saving
              ? "bg-gray-400 cursor-not-allowed"
              : "bg-blue-600 hover:bg-blue-700 shadow-md hover:shadow-lg"
          }`}>
          {saving ? "Creating..." : "Create Group"}
        </button>
      </div>
    </form>
  );
};

export default ModifierGroupForm;
