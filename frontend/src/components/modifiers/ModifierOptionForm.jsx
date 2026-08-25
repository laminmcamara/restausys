import React, { useState } from "react";
import api from "../../services/api";

const ModifierOptionForm = ({ groupId, onSuccess }) => {
  const [name, setName] = useState("");
  const [priceAdjustment, setPriceAdjustment] = useState("0");
  const [displayOrder, setDisplayOrder] = useState("0");
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!name.trim()) return;

    setSaving(true);
    try {
      // FIXED: Using centralized API service
      // Path matches /manager/modifier-options/
      await api.post("/manager/modifier-options/", {
        group: groupId,
        name: name.trim(),
        price_adjustment: parseFloat(priceAdjustment) || 0,
        display_order: parseInt(displayOrder) || 0,
      });

      setName("");
      setPriceAdjustment("0");
      setDisplayOrder("0");
      if (onSuccess) onSuccess();
    } catch (err) {
      console.error("Create Option Error:", err);
      alert(err.response?.data?.detail || "Failed to create option.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-wrap items-end gap-2 bg-gray-50 p-3 rounded-lg border border-gray-200">
      <div className="flex-1 min-w-[140px]">
        <label className="block text-[10px] font-bold text-gray-500 uppercase mb-1">
          Option Name
        </label>
        <input
          type="text"
          placeholder="e.g. Large, Extra Cheese"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          className="w-full border border-gray-300 p-1.5 text-sm rounded focus:ring-1 focus:ring-blue-500 outline-none"
        />
      </div>

      <div className="w-24">
        <label className="block text-[10px] font-bold text-gray-500 uppercase mb-1">
          Price +
        </label>
        <div className="relative">
          <span className="absolute left-2 top-1.5 text-gray-400 text-sm">
            $
          </span>
          <input
            type="number"
            step="0.01"
            value={priceAdjustment}
            onChange={(e) => setPriceAdjustment(e.target.value)}
            className="w-full border border-gray-300 p-1.5 pl-5 text-sm rounded focus:ring-1 focus:ring-blue-500 outline-none"
          />
        </div>
      </div>

      <div className="w-16">
        <label className="block text-[10px] font-bold text-gray-500 uppercase mb-1">
          Order
        </label>
        <input
          type="number"
          value={displayOrder}
          onChange={(e) => setDisplayOrder(e.target.value)}
          className="w-full border border-gray-300 p-1.5 text-sm rounded focus:ring-1 focus:ring-blue-500 outline-none text-center"
        />
      </div>

      <button
        type="submit"
        disabled={saving || !name.trim()}
        className={`px-4 py-2 text-sm font-bold text-white rounded transition ${
          saving || !name.trim()
            ? "bg-gray-300 cursor-not-allowed"
            : "bg-green-600 hover:bg-green-700 active:scale-95"
        }`}>
        {saving ? "..." : "Add"}
      </button>
    </form>
  );
};

export default ModifierOptionForm;
