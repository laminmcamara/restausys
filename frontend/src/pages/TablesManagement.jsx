import React, { useEffect, useState } from "react";
import {
  Plus,
  Trash2,
  Edit2,
  QrCode,
  Users,
  RefreshCw,
  X,
  MoreVertical,
} from "lucide-react";
import api from "../services/api";

export default function TablesManagement() {
  const [tables, setTables] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingTable, setEditingTable] = useState(null);
  const [tableNumber, setTableNumber] = useState("");
  const [capacity, setCapacity] = useState("");
  const [activeQrTable, setActiveQrTable] = useState(null);

  useEffect(() => {
    fetchTables();
    const interval = setInterval(fetchTables, 15000);
    return () => clearInterval(interval);
  }, []);

  const fetchTables = async () => {
    try {
      const res = await api.get("/tables/");
      setTables(res.data.results || res.data || []);
    } catch (err) {
      console.error("Error fetching tables:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    const payload = {
      table_number: tableNumber,
      capacity: parseInt(capacity) || 2,
    };
    try {
      if (editingTable) await api.put(`/tables/${editingTable.id}/`, payload);
      else await api.post("/tables/", payload);
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
        <p className="text-gray-500 font-medium">Loading floor plan...</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto bg-slate-50 min-h-screen">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">
            Tables
          </h1>
          <p className="text-slate-500 font-medium">
            Configure your restaurant layout and QR ordering.
          </p>
        </div>
        <button
          onClick={() => {
            setEditingTable(null);
            setTableNumber("");
            setCapacity("2");
            setShowModal(true);
          }}
          className="flex items-center justify-center gap-2 bg-indigo-600 text-white px-6 py-3 rounded-2xl font-bold hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-200">
          <Plus className="w-5 h-5" /> Add Table
        </button>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-4">
        {sortedTables.map((table) => {
          const occupied =
            table.has_active_session || table.status === "OCCUPIED";
          return (
            <div
              key={table.id}
              className="group bg-white rounded-[24px] border border-slate-200 p-5 hover:shadow-xl hover:shadow-slate-200/50 transition-all relative">
              {/* Top Row: Status & Actions */}
              <div className="flex justify-between items-start mb-6">
                <div
                  className={`px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider ${
                    occupied
                      ? "bg-orange-100 text-orange-600"
                      : "bg-emerald-100 text-emerald-600"
                  }`}>
                  {occupied ? "Occupied" : "Vacant"}
                </div>

                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => {
                      setEditingTable(table);
                      setTableNumber(table.table_number);
                      setCapacity(table.capacity);
                      setShowModal(true);
                    }}
                    className="p-1.5 text-slate-400 hover:text-indigo-600 transition-colors">
                    <Edit2 size={16} />
                  </button>
                  {!occupied && (
                    <button
                      onClick={() => handleDelete(table)}
                      className="p-1.5 text-slate-400 hover:text-rose-500 transition-colors">
                      <Trash2 size={16} />
                    </button>
                  )}
                </div>
              </div>

              {/* Center: Table Info */}
              <div className="text-center mb-6">
                <h2 className="text-4xl font-black text-slate-800 mb-1">
                  {table.table_number}
                </h2>
                <div className="flex items-center justify-center gap-1.5 text-slate-400 font-bold text-xs">
                  <Users size={14} />
                  <span>Seats {table.capacity}</span>
                </div>
              </div>

              {/* Bottom: QR Action */}
              <button
                onClick={() => setActiveQrTable(table)}
                className="w-full flex items-center justify-center gap-2 py-3 bg-slate-50 text-slate-600 rounded-xl hover:bg-indigo-50 hover:text-indigo-600 transition-all text-xs font-black uppercase tracking-widest border border-slate-100">
                <QrCode size={14} /> QR Code
              </button>
            </div>
          );
        })}
      </div>

      {/* Modals remain functionally the same but with updated styling */}
      {showModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-md flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-[32px] w-full max-w-md shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="p-8 border-b border-slate-50 flex justify-between items-center">
              <h2 className="text-2xl font-black text-slate-900">
                {editingTable ? "Edit Table" : "New Table"}
              </h2>
              <button
                onClick={() => setShowModal(false)}
                className="p-2 hover:bg-slate-100 rounded-full transition-colors">
                <X className="w-6 h-6 text-slate-400" />
              </button>
            </div>
            <form
              onSubmit={handleSave}
              className="p-8 space-y-5">
              <div>
                <label className="block text-xs font-black uppercase tracking-widest text-slate-400 mb-2">
                  Table Number
                </label>
                <input
                  type="text"
                  placeholder="e.g. 01"
                  value={tableNumber}
                  onChange={(e) => setTableNumber(e.target.value)}
                  required
                  className="w-full p-4 bg-slate-50 border-2 border-transparent focus:border-indigo-500 rounded-2xl outline-none transition-all font-bold text-slate-800"
                />
              </div>
              <div>
                <label className="block text-xs font-black uppercase tracking-widest text-slate-400 mb-2">
                  Capacity
                </label>
                <input
                  type="number"
                  value={capacity}
                  onChange={(e) => setCapacity(e.target.value)}
                  required
                  className="w-full p-4 bg-slate-50 border-2 border-transparent focus:border-indigo-500 rounded-2xl outline-none transition-all font-bold text-slate-800"
                />
              </div>
              <button
                type="submit"
                className="w-full py-4 bg-indigo-600 text-white rounded-2xl font-black shadow-lg shadow-indigo-200 hover:bg-indigo-700 transition-all">
                {editingTable ? "Save Changes" : "Create Table"}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* QR Modal - Simplified */}
      {activeQrTable && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-md flex items-center justify-center z-50 p-4">
          <div className="bg-white p-10 rounded-[40px] shadow-2xl text-center max-w-sm w-full relative animate-in fade-in slide-in-from-bottom-4 duration-300">
            <button
              onClick={() => setActiveQrTable(null)}
              className="absolute top-6 right-6 p-2 hover:bg-slate-100 rounded-full transition-colors">
              <X
                size={24}
                className="text-slate-300"
              />
            </button>
            <div className="mb-8">
              <h2 className="text-5xl font-black text-slate-900 mb-2">
                {activeQrTable.table_number}
              </h2>
              <p className="text-indigo-600 font-black tracking-[0.2em] uppercase text-[10px]">
                Digital Menu Access
              </p>
            </div>
            <div className="bg-slate-50 p-6 rounded-[32px] mb-8 border-2 border-dashed border-slate-200">
              {activeQrTable.qr_code ? (
                <img
                  src={activeQrTable.qr_code}
                  alt="QR"
                  className="w-48 h-48 mx-auto mix-blend-multiply"
                />
              ) : (
                <div className="h-48 flex flex-col items-center justify-center text-slate-400">
                  <QrCode
                    size={48}
                    className="mb-2 opacity-20"
                  />
                  <button
                    onClick={async () => {
                      try {
                        await api.post(
                          `/tables/${activeQrTable.id}/generate_qr/`
                        );
                        fetchTables();
                        setActiveQrTable(null);
                      } catch (err) {
                        alert("Failed");
                      }
                    }}
                    className="text-xs font-black text-indigo-600 underline">
                    Generate QR
                  </button>
                </div>
              )}
            </div>
            <button
              onClick={() => window.print()}
              className="w-full py-4 bg-slate-900 text-white rounded-2xl font-black hover:bg-black transition-all shadow-xl">
              Print QR Card
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
