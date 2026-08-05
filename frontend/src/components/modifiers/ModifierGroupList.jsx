import React from "react";
import ModifierOptionForm from "./ModifierOptionForm";
import {
  deleteModifierGroup,
  deleteModifierOption,
} from "../../services/modifierService";

const ModifierGroupList = ({ groups = [], token, onRefresh }) => {
  if (!groups.length) return <p>No modifier groups yet.</p>;

  const handleDeleteGroup = async (groupId) => {
    const confirmDelete = window.confirm(
      "Are you sure you want to delete this group? All its options will also be deleted."
    );
    if (!confirmDelete) return;

    try {
      await deleteModifierGroup(groupId, token);
      onRefresh();
    } catch (error) {
      console.error("Failed to delete group:", error);
    }
  };

  const handleDeleteOption = async (optionId) => {
    const confirmDelete = window.confirm("Delete this modifier option?");
    if (!confirmDelete) return;

    try {
      await deleteModifierOption(optionId, token);
      onRefresh();
    } catch (error) {
      console.error("Failed to delete option:", error);
    }
  };

  return (
    <div className="space-y-6">
      {groups.map((group) => (
        <div
          key={group.id}
          className="bg-white p-4 rounded shadow">
          {/* Header */}
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-lg font-semibold">{group.name}</h3>

            <button
              onClick={() => handleDeleteGroup(group.id)}
              className="text-red-600 text-sm hover:underline">
              Delete Group
            </button>
          </div>

          <p className="text-sm text-gray-600 mb-3">
            Type: {group.selection_type}
          </p>

          <h4 className="font-medium mb-2">Options</h4>

          {group.options?.length ? (
            <ul className="mb-3 space-y-2">
              {group.options.map((option) => (
                <li
                  key={option.id}
                  className="flex justify-between items-center border-b pb-1">
                  <span>
                    {option.name} (+{option.price_adjustment})
                  </span>

                  <button
                    onClick={() => handleDeleteOption(option.id)}
                    className="text-red-500 text-xs hover:underline">
                    Delete
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-500">No options yet.</p>
          )}

          {/* Add Option Form */}
          <ModifierOptionForm
            groupId={group.id}
            token={token}
            onSuccess={onRefresh}
          />
        </div>
      ))}
    </div>
  );
};

export default ModifierGroupList;
