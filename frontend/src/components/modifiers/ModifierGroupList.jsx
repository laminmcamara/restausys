import React from "react";
import ModifierOptionForm from "./ModifierOptionForm";
import api from "../../services/api";

const ModifierGroupList = ({ groups = [], onRefresh }) => {
  if (!groups.length) {
    return (
      <div className="text-center py-10 bg-white border border-dashed rounded-xl text-gray-500">
        No modifier groups yet. Create one to get started.
      </div>
    );
  }

  const handleDeleteGroup = async (groupId) => {
    const confirmDelete = window.confirm(
      "Are you sure you want to delete this group? All its options will also be deleted."
    );
    if (!confirmDelete) return;

    try {
      // FIXED: Using centralized API service
      await api.delete(`/manager/modifier-groups/${groupId}/`);
      onRefresh();
    } catch (error) {
      console.error("Failed to delete group:", error);
      alert("Failed to delete group. It might be linked to existing products.");
    }
  };

  const handleDeleteOption = async (optionId) => {
    if (!window.confirm("Delete this modifier option?")) return;

    try {
      // FIXED: Using centralized API service
      await api.delete(`/manager/modifier-options/${optionId}/`);
      onRefresh();
    } catch (error) {
      console.error("Failed to delete option:", error);
      alert("Failed to delete option.");
    }
  };

  return (
    <div className="space-y-6">
      {groups.map((group) => (
        <div
          key={group.id}
          className="bg-white border rounded-xl shadow-sm overflow-hidden">
          {/* Header */}
          <div className="bg-slate-50 px-4 py-3 border-b flex justify-between items-center">
            <div>
              <h3 className="text-lg font-bold text-gray-800">{group.name}</h3>
              <span
                className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                  group.selection_type === "SINGLE"
                    ? "bg-blue-100 text-blue-700"
                    : "bg-purple-100 text-purple-700"
                }`}>
                {group.selection_type === "SINGLE"
                  ? "Single Choice"
                  : "Multiple Choices"}
              </span>
            </div>

            <button
              onClick={() => handleDeleteGroup(group.id)}
              className="text-red-500 hover:text-red-700 p-2 transition"
              title="Delete Group">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round">
                <path d="M3 6h18" />
                <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
                <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
              </svg>
            </button>
          </div>

          <div className="p-4">
            <h4 className="text-sm font-bold text-gray-700 mb-3 uppercase tracking-wider">
              Available Options
            </h4>

            {group.options?.length ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-6">
                {group.options.map((option) => (
                  <div
                    key={option.id}
                    className="flex justify-between items-center bg-gray-50 border rounded-lg px-3 py-2 group">
                    <div className="flex flex-col">
                      <span className="text-sm font-medium text-gray-800">
                        {option.name}
                      </span>
                      <span className="text-xs text-green-600 font-bold">
                        +${Number(option.price_adjustment).toFixed(2)}
                      </span>
                    </div>

                    <button
                      onClick={() => handleDeleteOption(option.id)}
                      className="text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round">
                        <path d="M18 6 6 18" />
                        <path d="m6 6 12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-gray-400 italic mb-6">
                No options added yet.
              </div>
            )}

            {/* Add Option Form Section */}
            <div className="mt-4 pt-4 border-t">
              <p className="text-xs font-bold text-gray-500 mb-3 uppercase">
                Add New Option
              </p>
              <ModifierOptionForm
                groupId={group.id}
                onSuccess={onRefresh}
              />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default ModifierGroupList;
