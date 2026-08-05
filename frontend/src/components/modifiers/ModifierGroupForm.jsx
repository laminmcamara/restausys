import React, { useState } from "react";
import { createModifierGroup } from "../../services/modifierService";

const ModifierGroupForm = ({ token, onSuccess }) => {
  const [name, setName] = useState("");
  const [selectionType, setSelectionType] = useState("SINGLE");

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      await createModifierGroup(
        {
          name,
          selection_type: selectionType,
        },
        token
      );

      setName("");
      setSelectionType("SINGLE");
      onSuccess();
    } catch (err) {
      console.error(err);
      alert("Failed to create group.");
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="mb-6 bg-white p-4 rounded shadow">
      <h2 className="font-semibold mb-3">Create Modifier Group</h2>

      <input
        type="text"
        placeholder="Group Name (e.g. Size)"
        value={name}
        onChange={(e) => setName(e.target.value)}
        required
        className="border p-2 w-full mb-3 rounded"
      />

      <select
        value={selectionType}
        onChange={(e) => setSelectionType(e.target.value)}
        className="border p-2 w-full mb-3 rounded">
        <option value="SINGLE">Single Choice</option>
        <option value="MULTIPLE">Multiple Choices</option>
      </select>

      <button
        type="submit"
        className="bg-blue-600 text-white px-4 py-2 rounded">
        Create
      </button>
    </form>
  );
};

export default ModifierGroupForm;
