import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";

export default function TablesManagement() {
  const navigate = useNavigate();

  const [tables, setTables] = useState([]);
  const [loading, setLoading] = useState(true);

  const [showModal, setShowModal] = useState(false);
  const [editingTable, setEditingTable] = useState(null);

  const [tableNumber, setTableNumber] = useState("");
  const [capacity, setCapacity] = useState("");

  const [qrPreview, setQrPreview] = useState(null);

  useEffect(() => {
    fetchTables();

    const interval = setInterval(() => {
      fetchTables();
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  const fetchTables = async () => {
    try {
      const res = await api.get("/v1/tables/");
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
    setCapacity("");
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

    try {
      if (editingTable) {
        await api.put(`/tables/${editingTable.id}/`, {
          table_number: tableNumber,
          capacity: parseInt(capacity),
        });
      } else {
        await api.post("/v1/tables/", {
          table_number: tableNumber,
          capacity: parseInt(capacity),
        });
      }

      setShowModal(false);
      fetchTables();
    } catch (err) {
      console.error("Error saving table:", err.response?.data || err);
    }
  };

  const handleDelete = async (table) => {
    const confirmed = window.confirm(
      `Are you sure you want to delete ${table.table_number}?`
    );

    if (!confirmed) return;

    try {
      await api.delete(`/tables/${table.id}/`);
      fetchTables();
    } catch (err) {
      console.error("Error deleting table:", err.response?.data || err);
    }
  };

  const sortedTables = [...tables].sort((a, b) => {
    const numA = parseInt(a.table_number.replace(/\D/g, "")) || 0;
    const numB = parseInt(b.table_number.replace(/\D/g, "")) || 0;
    return numA - numB;
  });

  if (loading) {
    return (
      <div className="p-6 text-center text-gray-500">Loading tables...</div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Tables Management</h1>

        <button
          onClick={openCreateModal}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition">
          + Add Table
        </button>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-6">
        {sortedTables.map((table) => (
          <div
            key={table.id}
            onClick={() => navigate(`/pos/${table.id}`)}
            className="p-5 bg-gray-100 rounded-xl shadow hover:shadow-md transition cursor-pointer">
            <div className="flex justify-between items-start mb-2">
              <h2 className="text-lg font-semibold">{table.table_number}</h2>

              <span
                className={`text-xs px-2 py-1 rounded ${
                  table.has_active_session
                    ? "bg-red-100 text-red-700"
                    : "bg-green-100 text-green-700"
                }`}>
                {table.has_active_session ? "Occupied" : "Available"}
              </span>
            </div>

            <p className="text-sm text-gray-600 mb-3">
              Capacity: {table.capacity}
            </p>

            {/* Open POS Button */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                navigate(`/pos/${table.id}`);
              }}
              className="w-full mb-3 bg-indigo-600 text-white text-sm py-1.5 rounded hover:bg-indigo-700 transition">
              Open POS
            </button>

            {/* QR Section */}
            <div className="mb-3 text-center">
              {table.qr_code ? (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setQrPreview(table.qr_code);
                  }}
                  className="text-xs text-indigo-600 hover:underline">
                  View QR
                </button>
              ) : (
                <button
                  onClick={async (e) => {
                    e.stopPropagation();
                    try {
                      await api.post(`/tables/${table.id}/generate_qr/`);
                      fetchTables();
                    } catch (err) {
                      console.error("QR generation failed", err);
                    }
                  }}
                  className="text-xs text-green-600 hover:underline">
                  Generate QR
                </button>
              )}
            </div>

            {/* Edit/Delete */}
            <div className="flex justify-between">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  openEditModal(table);
                }}
                className="text-blue-600 hover:underline text-sm">
                Edit
              </button>

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(table);
                }}
                disabled={table.has_active_session}
                className={`text-sm ${
                  table.has_active_session
                    ? "text-gray-400 cursor-not-allowed"
                    : "text-red-600 hover:underline"
                }`}>
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg w-full max-w-md shadow-lg">
            <h2 className="text-xl font-semibold mb-4">
              {editingTable ? "Edit Table" : "Create Table"}
            </h2>
            <div className="mb-4">
              <span
                className={`px-3 py-1 text-xs rounded ${
                  order.status === "DRAFT"
                    ? "bg-gray-200 text-gray-700"
                    : order.status === "IN_PROGRESS"
                    ? "bg-orange-100 text-orange-700"
                    : order.status === "PAID"
                    ? "bg-green-100 text-green-700"
                    : "bg-blue-100 text-blue-700"
                }`}>
                {order.status}
              </span>
            </div>
            <form
              onSubmit={handleSave}
              className="space-y-4">
              <input
                type="text"
                placeholder="Table Number (e.g. T11)"
                value={tableNumber}
                onChange={(e) => setTableNumber(e.target.value)}
                required
                className="w-full p-2 border rounded"
              />

              <input
                type="number"
                placeholder="Capacity"
                value={capacity}
                onChange={(e) => setCapacity(e.target.value)}
                required
                className="w-full p-2 border rounded"
              />

              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 bg-gray-200 rounded">
                  Cancel
                </button>

                <button
                  type="submit"
                  className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">
                  Save
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* QR Modal */}
      {qrPreview && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-lg text-center">
            <h2 className="text-lg font-semibold mb-4">QR Code</h2>

            <img
              src={qrPreview}
              alt="QR Code"
              className="w-48 h-48 mx-auto mb-4"
            />

            <button
              onClick={() => setQrPreview(null)}
              className="px-4 py-2 bg-gray-200 rounded">
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
