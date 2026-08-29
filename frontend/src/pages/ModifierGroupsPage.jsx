import React, { useState, useEffect } from "react";
import {
  Plus,
  Trash2,
  RefreshCw,
  Layers,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import api from "../services/api";

const ModifierGroupsPage = () => {
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [newGroup, setNewGroup] = useState({
    name: "",
    selection_type: "SINGLE",
    is_required: false,
  });

  useEffect(() => {
    fetchGroups();
  }, []);

  const fetchGroups = async () => {
    setLoading(true);
    setError(null);
    try {
      // Using the endpoint we registered in urls.py
      const res = await api.get("/manager/modifiers/");
      const data = res.data.results || res.data || [];
      setGroups(data);
    } catch (err) {
      console.error("Failed to fetch modifier groups", err);
      setError("Could not load modifier groups. Please check your connection.");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateGroup = async (e) => {
    e.preventDefault();
    try {
      const res = await api.post("/manager/modifiers/", newGroup);
      setGroups([...groups, res.data]);
      setNewGroup({ name: "", selection_type: "SINGLE", is_required: false });
    } catch (err) {
      alert("Error creating group. Make sure the name is unique.");
    }
  };

  const handleDeleteGroup = async (id) => {
    if (!window.confirm("Delete this group and all its options?")) return;
    try {
      await api.delete(`/manager/modifiers/${id}/`);
      setGroups(groups.filter((g) => g.id !== id));
    } catch (err) {
      console.error("Delete failed", err);
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Layers className="w-6 h-6 text-indigo-600" />
            Modifier Groups
          </h1>
          <p className="text-gray-500 text-sm">
            Create groups like "Size" or "Extra Toppings" to customize your
            products.
          </p>
        </div>
        <button
          onClick={fetchGroups}
          className="p-2 text-gray-500 hover:bg-gray-100 rounded-full transition-transform active:rotate-180">
          <RefreshCw className={`w-5 h-5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-md flex items-center gap-2">
          <AlertCircle className="w-5 h-5" />
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left: Create Form */}
        <div className="lg:col-span-1">
          <div className="bg-white p-6 rounded-xl shadow-sm border sticky top-6">
            <h2 className="text-lg font-semibold mb-4">New Group</h2>
            <form
              onSubmit={handleCreateGroup}
              className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Group Name
                </label>
                <input
                  type="text"
                  value={newGroup.name}
                  onChange={(e) =>
                    setNewGroup({ ...newGroup, name: e.target.value })
                  }
                  placeholder="e.g. Extra Toppings"
                  className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Selection Type
                </label>
                <select
                  className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                  value={newGroup.selection_type}
                  onChange={(e) =>
                    setNewGroup({ ...newGroup, selection_type: e.target.value })
                  }>
                  <option value="SINGLE">Single Choice (Radio)</option>
                  <option value="MULTIPLE">Multiple Choice (Checkbox)</option>
                </select>
              </div>

              <div className="flex items-center gap-2 p-2 bg-gray-50 rounded-lg">
                <input
                  type="checkbox"
                  id="is_required"
                  checked={newGroup.is_required}
                  onChange={(e) =>
                    setNewGroup({ ...newGroup, is_required: e.target.checked })
                  }
                  className="w-4 h-4 text-indigo-600"
                />
                <label
                  htmlFor="is_required"
                  className="text-sm font-medium text-gray-700 cursor-pointer">
                  Required for customer?
                </label>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-indigo-600 text-white py-2.5 rounded-lg hover:bg-indigo-700 transition flex items-center justify-center gap-2 font-medium">
                <Plus className="w-4 h-4" /> Create Group
              </button>
            </form>
          </div>
        </div>

        {/* Right: List of Groups */}
        <div className="lg:col-span-2 space-y-6">
          {groups.length === 0 && !loading ? (
            <div className="text-center py-12 bg-gray-50 rounded-xl border-2 border-dashed">
              <Layers className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">
                No modifier groups yet. Create your first one on the left.
              </p>
            </div>
          ) : (
            groups.map((group) => (
              <div
                key={group.id}
                className="bg-white border rounded-xl shadow-sm overflow-hidden">
                <div className="p-4 bg-gray-50 border-b flex justify-between items-center">
                  <div>
                    <h3 className="font-bold text-gray-800 text-lg">
                      {group.name}
                    </h3>
                    <div className="flex gap-2 mt-1">
                      <span className="text-[10px] bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full font-bold uppercase">
                        {group.selection_type}
                      </span>
                      {group.is_required && (
                        <span className="text-[10px] bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-bold uppercase">
                          Required
                        </span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => handleDeleteGroup(group.id)}
                    className="text-gray-400 hover:text-red-500 p-2 hover:bg-red-50 rounded-full transition-colors">
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>

                <div className="p-4">
                  <ModifierOptionsList
                    groupId={group.id}
                    initialOptions={group.options || []}
                  />
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

const ModifierOptionsList = ({ groupId, initialOptions }) => {
  const [options, setOptions] = useState(initialOptions);
  const [newOpt, setNewOpt] = useState({ name: "", price_override: "0.00" });
  const [isAdding, setIsAdding] = useState(false);

  const addOption = async (e) => {
    e.preventDefault();
    if (!newOpt.name) return;
    setIsAdding(true);
    try {
      const res = await api.post("/manager/modifier-options/", {
        ...newOpt,
        group: groupId,
      });
      setOptions([...options, res.data]);
      setNewOpt({ name: "", price_override: "0.00" });
    } catch (err) {
      console.error(err);
    } finally {
      setIsAdding(false);
    }
  };

  const deleteOption = async (optId) => {
    try {
      await api.delete(`/manager/modifier-options/${optId}/`);
      setOptions(options.filter((o) => o.id !== optId));
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-3">
      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
        Options / Choices
      </h4>
      <div className="grid grid-cols-1 gap-2">
        {options.map((opt) => (
          <div
            key={opt.id}
            className="flex justify-between items-center text-sm p-3 bg-gray-50 rounded-lg border border-gray-100 group">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-green-500" />
              <span className="font-medium text-gray-700">{opt.name}</span>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-indigo-600 font-semibold">
                +${parseFloat(opt.price_override).toFixed(2)}
              </span>
              <button
                onClick={() => deleteOption(opt.id)}
                className="text-gray-300 hover:text-red-500 transition-colors">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>

      <form
        onSubmit={addOption}
        className="flex gap-2 mt-4 pt-4 border-t border-dashed">
        <input
          placeholder="Option (e.g. Extra Cheese)"
          className="flex-1 text-sm p-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
          value={newOpt.name}
          onChange={(e) => setNewOpt({ ...newOpt, name: e.target.value })}
          required
        />
        <div className="relative w-28">
          <span className="absolute left-2 top-2 text-gray-400 text-sm">$</span>
          <input
            type="number"
            step="0.01"
            placeholder="0.00"
            className="w-full text-sm p-2 pl-5 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
            value={newOpt.price_override}
            onChange={(e) =>
              setNewOpt({ ...newOpt, price_override: e.target.value })
            }
          />
        </div>
        <button
          type="submit"
          disabled={isAdding}
          className="bg-gray-900 text-white px-4 py-2 rounded-lg text-sm hover:bg-black transition flex items-center gap-2 disabled:opacity-50">
          Add
        </button>
      </form>
    </div>
  );
};

export default ModifierGroupsPage;
