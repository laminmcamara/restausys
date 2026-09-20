import React, { useCallback, useEffect, useMemo, useState } from "react";

import { Edit2, Plus, QrCode, RefreshCw, Trash2, Users, X } from "lucide-react";

import api from "../services/api";

const TABLE_FETCH_INTERVAL = 15000;

const getErrorMessage = (error, fallback = "Something went wrong.") => {
  const data = error?.response?.data;

  if (typeof data === "string") {
    return data;
  }

  if (data?.detail) {
    return data.detail;
  }

  if (data?.error) {
    return data.error;
  }

  if (data && typeof data === "object") {
    return Object.entries(data)
      .map(([key, value]) => {
        const message = Array.isArray(value) ? value.join(" ") : String(value);

        return `${key}: ${message}`;
      })
      .join(" | ");
  }

  return error?.message || fallback;
};

const getResponseList = (response) => {
  const payload = response?.data;

  if (Array.isArray(payload)) {
    return payload;
  }

  if (Array.isArray(payload?.results)) {
    return payload.results;
  }

  return [];
};

const normalizeStatus = (table) => {
  const status = String(table?.current_status || table?.status || "")
    .trim()
    .toUpperCase();

  if (
    table?.has_active_session &&
    !["RESERVED", "NEEDS_CLEANING", "MERGED"].includes(status)
  ) {
    return "OCCUPIED";
  }

  return status || "AVAILABLE";
};

const isOccupied = (table) => {
  return normalizeStatus(table) === "OCCUPIED";
};

const isUnavailable = (table) => {
  return ["OCCUPIED", "RESERVED", "NEEDS_CLEANING", "MERGED"].includes(
    normalizeStatus(table)
  );
};

const getStatusLabel = (table) => {
  const status = normalizeStatus(table);

  const labels = {
    AVAILABLE: "Available",
    OCCUPIED: "Occupied",
    NEEDS_CLEANING: "Needs Cleaning",
    RESERVED: "Reserved",
    MERGED: "Merged",
  };

  return labels[status] || status;
};

const getStatusClasses = (table) => {
  const status = normalizeStatus(table);

  if (status === "OCCUPIED") {
    return "bg-orange-100 text-orange-700";
  }

  if (status === "NEEDS_CLEANING") {
    return "bg-amber-100 text-amber-700";
  }

  if (status === "RESERVED") {
    return "bg-blue-100 text-blue-700";
  }

  if (status === "MERGED") {
    return "bg-purple-100 text-purple-700";
  }

  return "bg-emerald-100 text-emerald-700";
};

const tableSortValue = (table) => {
  const value = String(table?.table_number || "");

  const numericPart = value.replace(/\D/g, "");

  return parseInt(numericPart, 10) || 0;
};

export default function TablesManagement() {
  const [tables, setTables] = useState([]);

  const [loading, setLoading] = useState(true);

  const [isRefreshing, setIsRefreshing] = useState(false);

  const [isSaving, setIsSaving] = useState(false);

  const [showModal, setShowModal] = useState(false);

  const [editingTable, setEditingTable] = useState(null);

  const [tableNumber, setTableNumber] = useState("");

  const [capacity, setCapacity] = useState("4");

  const [activeQrTable, setActiveQrTable] = useState(null);

  const [error, setError] = useState("");

  const [successMessage, setSuccessMessage] = useState("");

  const fetchTables = useCallback(async (isManual = false, signal) => {
    if (isManual) {
      setIsRefreshing(true);
    }

    try {
      setError("");

      const response = await api.get("/tables/", {
        signal,
        params: {
          _: Date.now(),
        },
      });

      const data = getResponseList(response);

      // Replace state; do not append old tables.
      setTables(data);
    } catch (requestError) {
      if (
        requestError?.code === "ERR_CANCELED" ||
        requestError?.name === "CanceledError"
      ) {
        return;
      }

      console.error("Error fetching tables:", requestError);

      setError(getErrorMessage(requestError, "Error fetching tables."));
    } finally {
      if (!signal || !signal.aborted) {
        setLoading(false);

        if (isManual) {
          setIsRefreshing(false);
        }
      }
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    fetchTables(false, controller.signal);

    const interval = setInterval(() => {
      fetchTables(false);
    }, TABLE_FETCH_INTERVAL);

    return () => {
      controller.abort();
      clearInterval(interval);
    };
  }, [fetchTables]);

  const openCreateModal = () => {
    setEditingTable(null);
    setTableNumber("");
    setCapacity("4");
    setError("");
    setSuccessMessage("");
    setShowModal(true);
  };

  const openEditModal = (table) => {
    setEditingTable(table);
    setTableNumber(String(table?.table_number || ""));
    setCapacity(String(table?.capacity || 4));
    setError("");
    setSuccessMessage("");
    setShowModal(true);
  };

  const closeModal = () => {
    if (isSaving) {
      return;
    }

    setShowModal(false);
    setEditingTable(null);
    setTableNumber("");
    setCapacity("4");
  };

  const handleSave = async (event) => {
    event.preventDefault();

    const cleanTableNumber = tableNumber.trim();

    const numericCapacity = Number(capacity);

    if (!cleanTableNumber) {
      setError("Table number is required.");
      return;
    }

    if (!Number.isInteger(numericCapacity) || numericCapacity <= 0) {
      setError("Capacity must be a positive whole number.");
      return;
    }

    setIsSaving(true);
    setError("");
    setSuccessMessage("");

    const payload = {
      table_number: cleanTableNumber,
      capacity: numericCapacity,
    };

    try {
      if (editingTable) {
        await api.patch(`/tables/${editingTable.id}/`, payload);

        setSuccessMessage("Table updated successfully.");
      } else {
        await api.post("/tables/", payload);

        setSuccessMessage("Table created successfully.");
      }

      await fetchTables();

      setShowModal(false);
      setEditingTable(null);
      setTableNumber("");
      setCapacity("4");
    } catch (requestError) {
      console.error(
        "Error saving table:",
        requestError?.response?.data || requestError
      );

      setError(getErrorMessage(requestError, "Error saving table."));
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (table) => {
    if (isUnavailable(table)) {
      window.alert("Only available tables can be deleted.");
      return;
    }

    const confirmed = window.confirm(`Delete table ${table.table_number}?`);

    if (!confirmed) {
      return;
    }

    try {
      setError("");

      await api.delete(`/tables/${table.id}/`);

      setSuccessMessage("Table deleted successfully.");

      await fetchTables();
    } catch (requestError) {
      console.error(
        "Error deleting table:",
        requestError?.response?.data || requestError
      );

      setError(getErrorMessage(requestError, "Error deleting table."));
    }
  };

  const handleGenerateQr = async (table) => {
    try {
      setError("");

      const response = await api.post(`/tables/${table.id}/generate_qr/`);

      const updatedTable = response.data?.table || response.data;

      if (updatedTable?.id) {
        setActiveQrTable(updatedTable);
      } else {
        await fetchTables();
      }

      setSuccessMessage("QR code generated successfully.");
    } catch (requestError) {
      console.error(
        "QR generation failed:",
        requestError?.response?.data || requestError
      );

      setError(getErrorMessage(requestError, "Failed to generate QR code."));
    }
  };

  const sortedTables = useMemo(() => {
    return [...tables].sort((first, second) => {
      const firstValue = tableSortValue(first);

      const secondValue = tableSortValue(second);

      if (firstValue !== secondValue) {
        return firstValue - secondValue;
      }

      return String(first?.table_number || "").localeCompare(
        String(second?.table_number || "")
      );
    });
  }, [tables]);

  if (loading && tables.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin mb-2" />

        <p className="text-gray-500 font-medium">Loading floor plan...</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto bg-slate-50 min-h-screen">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">
            Tables
          </h1>

          <p className="text-slate-500 font-medium">
            Configure your restaurant layout and QR ordering.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => {
              fetchTables(true);
            }}
            disabled={isRefreshing}
            className="inline-flex items-center justify-center gap-2 bg-white text-slate-700 px-4 py-3 rounded-2xl font-bold border border-slate-200 hover:bg-slate-100 transition-all disabled:opacity-50">
            <RefreshCw
              size={18}
              className={isRefreshing ? "animate-spin" : ""}
            />
            Refresh
          </button>

          <button
            type="button"
            onClick={openCreateModal}
            className="flex items-center justify-center gap-2 bg-indigo-600 text-white px-6 py-3 rounded-2xl font-bold hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-200">
            <Plus className="w-5 h-5" />
            Add Table
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-5 bg-red-50 border border-red-100 text-red-700 rounded-2xl p-4 font-bold">
          {error}
        </div>
      )}

      {successMessage && (
        <div className="mb-5 bg-emerald-50 border border-emerald-100 text-emerald-700 rounded-2xl p-4 font-bold">
          {successMessage}
        </div>
      )}

      {sortedTables.length === 0 ? (
        <div className="bg-white border-2 border-dashed border-slate-200 rounded-[32px] p-20 text-center">
          <p className="text-slate-400 text-lg font-bold">No tables found.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {sortedTables.map((table) => {
            const status = normalizeStatus(table);

            const occupied = status === "OCCUPIED";

            const canDelete = status === "AVAILABLE";

            return (
              <div
                key={String(table.id)}
                className="group bg-white rounded-[24px] border border-slate-200 p-5 hover:shadow-xl hover:shadow-slate-200/50 transition-all relative">
                <div className="flex justify-between items-start mb-6">
                  <div
                    className={`px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider ${getStatusClasses(
                      table
                    )}`}>
                    {getStatusLabel(table)}
                  </div>

                  <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      type="button"
                      onClick={() => {
                        openEditModal(table);
                      }}
                      className="p-1.5 text-slate-400 hover:text-indigo-600 transition-colors"
                      aria-label={`Edit table ${table.table_number}`}>
                      <Edit2 size={16} />
                    </button>

                    {canDelete && (
                      <button
                        type="button"
                        onClick={() => {
                          handleDelete(table);
                        }}
                        className="p-1.5 text-slate-400 hover:text-rose-500 transition-colors"
                        aria-label={`Delete table ${table.table_number}`}>
                        <Trash2 size={16} />
                      </button>
                    )}
                  </div>
                </div>

                <div className="text-center mb-6">
                  <h2 className="text-4xl font-black text-slate-800 mb-1">
                    {table.table_number}
                  </h2>

                  <div className="flex items-center justify-center gap-1.5 text-slate-400 font-bold text-xs">
                    <Users size={14} />

                    <span>Seats {table.capacity}</span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    setActiveQrTable(table);
                    setError("");
                    setSuccessMessage("");
                  }}
                  className="w-full flex items-center justify-center gap-2 py-3 bg-slate-50 text-slate-600 rounded-xl hover:bg-indigo-50 hover:text-indigo-600 transition-all text-xs font-black uppercase tracking-widest border border-slate-100">
                  <QrCode size={14} />
                  QR Code
                </button>

                {occupied && (
                  <p className="mt-3 text-center text-xs font-bold text-orange-600">
                    Active session
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-md flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-[32px] w-full max-w-md shadow-2xl overflow-hidden">
            <div className="p-8 border-b border-slate-50 flex justify-between items-center">
              <h2 className="text-2xl font-black text-slate-900">
                {editingTable ? "Edit Table" : "New Table"}
              </h2>

              <button
                type="button"
                onClick={closeModal}
                disabled={isSaving}
                className="p-2 hover:bg-slate-100 rounded-full transition-colors disabled:opacity-50">
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
                  onChange={(event) => {
                    setTableNumber(event.target.value);
                  }}
                  required
                  disabled={isSaving}
                  className="w-full p-4 bg-slate-50 border-2 border-transparent focus:border-indigo-500 rounded-2xl outline-none transition-all font-bold text-slate-800 disabled:opacity-50"
                />
              </div>

              <div>
                <label className="block text-xs font-black uppercase tracking-widest text-slate-400 mb-2">
                  Capacity
                </label>

                <input
                  type="number"
                  min="1"
                  value={capacity}
                  onChange={(event) => {
                    setCapacity(event.target.value);
                  }}
                  required
                  disabled={isSaving}
                  className="w-full p-4 bg-slate-50 border-2 border-transparent focus:border-indigo-500 rounded-2xl outline-none transition-all font-bold text-slate-800 disabled:opacity-50"
                />
              </div>

              <button
                type="submit"
                disabled={isSaving}
                className="w-full py-4 bg-indigo-600 text-white rounded-2xl font-black shadow-lg shadow-indigo-200 hover:bg-indigo-700 transition-all disabled:opacity-50">
                {isSaving
                  ? "Saving..."
                  : editingTable
                  ? "Save Changes"
                  : "Create Table"}
              </button>
            </form>
          </div>
        </div>
      )}

      {activeQrTable && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-md flex items-center justify-center z-50 p-4">
          <div className="bg-white p-10 rounded-[40px] shadow-2xl text-center max-w-sm w-full relative">
            <button
              type="button"
              onClick={() => {
                setActiveQrTable(null);
              }}
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
                  alt={`QR code for table ${activeQrTable.table_number}`}
                  className="w-48 h-48 mx-auto mix-blend-multiply"
                />
              ) : (
                <div className="h-48 flex flex-col items-center justify-center text-slate-400">
                  <QrCode
                    size={48}
                    className="mb-2 opacity-20"
                  />

                  <button
                    type="button"
                    onClick={() => {
                      handleGenerateQr(activeQrTable);
                    }}
                    className="text-xs font-black text-indigo-600 underline">
                    Generate QR
                  </button>
                </div>
              )}
            </div>

            {activeQrTable.qr_code && (
              <button
                type="button"
                onClick={() => {
                  window.print();
                }}
                className="w-full py-4 bg-slate-900 text-white rounded-2xl font-black hover:bg-black transition-all shadow-xl">
                Print QR Card
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
