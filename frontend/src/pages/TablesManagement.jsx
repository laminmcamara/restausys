import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Plus,
  Trash2,
  Edit2,
  QrCode,
  Users,
  ExternalLink,
  RefreshCw,
  X,
} from "lucide-react";
import api from "../services/api";

export default function TablesManagement() {
  const navigate = useNavigate();
  const [tables, setTables] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingTable, setEditingTable] = useState(null);
  const [tableNumber, setTableNumber] = useState("");
  const [capacity, setCapacity] = useState("");
  const [activeQrTable, setActiveQrTable] = useState(null);

  useEffect(() => {
    fetchTables();
    const interval = setInterval(fetchTables, 15000); // Poll every 15s
    return () => clearInterval(interval);
  }, []);

  const fetchTables = async () => {
    try {
      const res = await api.get("/tables/");
      setTables(res.data.results || res.data);
    } catch (err) {
      console.error("Error fetching tables:", err);
    } finally {
      setLoading(false);
    }
  };

  const openCreateModal = () => {
    setEditingTable(null);
    setTableNumber("");
    setCapacity("2");
    setShowModal(true);
  };

  const openEditModal = (table) => {
    setEditingTable(table);
    setTableNumber(table.table_number);
    setCapacity(table.capacity);
    setShowModal(true);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    const payload = {
      table_number: tableNumber,
      capacity: parseInt(capacity) || 2,
    };

    try {
      if (editingTable) {
        await api.put(`/tables/${editingTable.id}/`, payload);
      } else {
        await api.post("/tables/", payload);
      }
      setShowModal(false);
      fetchTables();
    } catch (err) {
      alert("Error saving table. Ensure the table number is unique.");
    }
  };

  const handleDelete = async (table) => {
    if (!window.confirm(`Delete ${table.table_number}?`)) return;
    try {
      await api.delete(`/tables/${table.id}/`);
      fetchTables();
    } catch (err) {
      console.error("Error deleting table:", err);
    }
  };

  const sortedTables = [...tables].sort((a, b) => {
    const numA = parseInt(a.table_number.replace(/\D/g, "")) || 0;
    const numB = parseInt(b.table_number.replace(/\D/g, "")) || 0;
    return numA - numB;
  });

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin mb-2" />
        <p className="text-gray-500 font-medium">Loading your floor plan...</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Tables</h1>
          <p className="text-gray-500">
            Manage your restaurant floor and QR codes.
          </p>
        </div>
        <button
          onClick={openCreateModal}
          className="flex items-center justify-center gap-2 bg-indigo-600 text-white px-6 py-3 rounded-xl font-bold hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-200">
          <Plus className="w-5 h-5" /> Add New Table
        </button>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-6">
        {sortedTables.map((table) => (
          <div
            key={table.id}
            className="group relative bg-white rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition-all overflow-hidden">
            {/* Status Bar */}
            <div
              className={`h-1.5 w-full ${
                table.has_active_session ? "bg-rose-500" : "bg-emerald-500"
              }`}
            />

            <div className="p-5">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h2 className="text-xl font-bold text-gray-800">
                    {table.table_number}
                  </h2>
                  <div className="flex items-center gap-1.5 text-gray-500 mt-1">
                    <Users className="w-4 h-4" />
                    <span className="text-sm font-medium">
                      Seats {table.capacity}
                    </span>
                  </div>
                </div>
                <span
                  className={`text-[10px] uppercase tracking-wider font-bold px-2 py-1 rounded-md ${
                    table.has_active_session
                      ? "bg-rose-50 text-rose-600"
                      : "bg-emerald-50 text-emerald-600"
                  }`}>
                  {table.has_active_session ? "Occupied" : "Available"}
                </span>
              </div>

              <div className="space-y-2">
                <button
                  onClick={() => navigate(`/pos/${table.id}`)}
                  className="w-full flex items-center justify-center gap-2 bg-gray-900 text-white py-2 rounded-lg hover:bg-black transition text-sm font-semibold">
                  <ExternalLink className="w-4 h-4" /> Open POS
                </button>

                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => setActiveQrTable(table)}
                    className="flex items-center justify-center gap-1.5 py-2 bg-indigo-50 text-indigo-600 rounded-lg hover:bg-indigo-100 transition text-xs font-bold">
                    <QrCode className="w-3.5 h-3.5" /> QR Code
                  </button>
                  <button
                    onClick={() => openEditModal(table)}
                    className="flex items-center justify-center gap-1.5 py-2 bg-gray-50 text-gray-600 rounded-lg hover:bg-gray-100 transition text-xs font-bold">
                    <Edit2 className="w-3.5 h-3.5" /> Edit
                  </button>
                </div>
              </div>

              {/* Delete Button - Absolute positioned to show on hover */}
              {!table.has_active_session && (
                <button
                  onClick={() => handleDelete(table)}
                  className="absolute top-2 right-2 p-1.5 text-gray-300 hover:text-rose-500 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-gray-900/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">
            <div className="p-6 border-b flex justify-between items-center">
              <h2 className="text-xl font-bold text-gray-800">
                {editingTable ? "Edit Table" : "Create New Table"}
              </h2>
              <button
                onClick={() => setShowModal(false)}
                className="text-gray-400 hover:text-gray-600">
                <X className="w-6 h-6" />
              </button>
            </div>

            <form
              onSubmit={handleSave}
              className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">
                  Table Name / Number
                </label>
                <input
                  type="text"
                  placeholder="e.g. Table 01"
                  value={tableNumber}
                  onChange={(e) => setTableNumber(e.target.value)}
                  required
                  className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none transition"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">
                  Seating Capacity
                </label>
                <input
                  type="number"
                  value={capacity}
                  onChange={(e) => setCapacity(e.target.value)}
                  required
                  className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none transition"
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 py-3 bg-gray-100 text-gray-600 rounded-xl font-bold hover:bg-gray-200 transition">
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-3 bg-indigo-600 text-white rounded-xl font-bold hover:bg-indigo-700 transition shadow-lg shadow-indigo-100">
                  {editingTable ? "Update Table" : "Create Table"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* QR Modal */}
      {activeQrTable && (
        <div className="fixed inset-0 bg-gray-900/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white p-8 rounded-3xl shadow-2xl text-center max-w-sm w-full relative">
            <button
              onClick={() => setActiveQrTable(null)}
              className="absolute top-4 right-4 text-gray-400 hover:text-gray-600">
              <X className="w-6 h-6" />
            </button>

            <div className="mb-6">
              <div className="w-16 h-16 bg-indigo-50 rounded-full flex items-center justify-center mx-auto mb-4">
                <QrCode className="w-8 h-8 text-indigo-600" />
              </div>
              <h2 className="text-3xl font-black text-gray-900">
                {activeQrTable.table_number}
              </h2>
              <p className="text-indigo-600 font-bold tracking-widest uppercase text-xs mt-1">
                Scan to Order
              </p>
            </div>

            <div className="bg-white p-4 rounded-2xl mb-8 border-2 border-dashed border-gray-200 inline-block">
              {activeQrTable.qr_code ? (
                <img
                  src={activeQrTable.qr_code}
                  alt="QR Code"
                  className="w-48 h-48 mx-auto"
                />
              ) : (
                <div className="w-48 h-48 flex flex-col items-center justify-center gap-2">
                  <p className="text-sm text-gray-400">No QR generated</p>
                  <button
                    onClick={async () => {
                      try {
                        await api.post(
                          `/tables/${activeQrTable.id}/generate_qr/`
                        );
                        fetchTables();
                        setActiveQrTable(null); // Close to refresh
                      } catch (err) {
                        alert("Failed to generate");
                      }
                    }}
                    className="text-xs text-indigo-600 font-bold underline">
                    Generate Now
                  </button>
                </div>
              )}
            </div>

            <div className="flex flex-col gap-3">
              <button
                onClick={() => window.print()}
                className="w-full py-4 bg-indigo-600 text-white rounded-2xl font-bold hover:bg-indigo-700 transition shadow-lg shadow-indigo-200 flex items-center justify-center gap-2">
                Print QR Card
              </button>
              <p className="text-[10px] text-gray-400">
                BEEPOS Digital Menu System
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
