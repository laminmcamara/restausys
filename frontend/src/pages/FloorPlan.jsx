import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertCircle, Armchair, Loader2, RefreshCw } from "lucide-react";

import api from "../services/api";

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

const isCanceledRequest = (error) => {
  return (
    error?.code === "ERR_CANCELED" ||
    error?.name === "CanceledError" ||
    error?.name === "AbortError"
  );
};

const getErrorMessage = (error, fallback) => {
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

const normalizeTableStatus = (value) => {
  const status = String(value || "AVAILABLE")
    .trim()
    .toUpperCase();

  if (status === "VACANT") {
    return "AVAILABLE";
  }

  if (status === "IN_USE") {
    return "OCCUPIED";
  }

  return status;
};

const normalizeTable = (table) => {
  const status = normalizeTableStatus(table?.current_status ?? table?.status);

  const blockedStatuses = ["NEEDS_CLEANING", "MERGED", "INACTIVE"];

  const isOccupied =
    Boolean(table?.is_occupied) ||
    Boolean(table?.has_active_session) ||
    status === "OCCUPIED";

  const isBlocked = blockedStatuses.includes(status);

  const capacity = Number(table?.capacity ?? table?.seats ?? 0);

  return {
    ...table,
    status,
    current_status: status,
    is_occupied: isOccupied,
    is_available: table?.is_available !== false && !isBlocked,
    is_blocked: isBlocked,
    display_number:
      table?.table_number ?? table?.number ?? table?.name ?? table?.id,
    display_capacity: Number.isFinite(capacity) ? capacity : 0,
  };
};

const getStatusLabel = (table) => {
  if (table.is_blocked) {
    if (table.current_status === "NEEDS_CLEANING") {
      return "Needs Cleaning";
    }

    if (table.current_status === "MERGED") {
      return "Merged";
    }

    return "Unavailable";
  }

  if (table.is_occupied) {
    return "Occupied";
  }

  return "Available";
};

const getTableClasses = (table) => {
  if (table.is_blocked) {
    return {
      border: "border-slate-300",
      background: "bg-slate-200",
      text: "text-slate-500",
      badge: "bg-slate-400 text-white",
    };
  }

  if (table.is_occupied) {
    return {
      border: "border-red-300",
      background: "bg-red-100",
      text: "text-red-800",
      badge: "bg-red-600 text-white",
    };
  }

  return {
    border: "border-green-300",
    background: "bg-green-100",
    text: "text-green-800",
    badge: "bg-green-600 text-white",
  };
};

export default function FloorPlan() {
  const [tables, setTables] = useState([]);

  const [loadingTables, setLoadingTables] = useState(true);

  const [refreshing, setRefreshing] = useState(false);

  const [error, setError] = useState("");
  const navigate = useNavigate();
  const fetchTables = useCallback(async (signal) => {
    setRefreshing(true);

    try {
      const response = await api.get("/tables/", {
        signal,
        params: {
          _: Date.now(),
        },
      });

      const tableData = getResponseList(response).map(normalizeTable);

      setTables(tableData);
      setError("");
    } catch (requestError) {
      if (isCanceledRequest(requestError)) {
        return;
      }

      console.error("Failed to load tables:", requestError);

      setError(getErrorMessage(requestError, "Failed to load tables."));
    } finally {
      if (!signal || !signal.aborted) {
        setLoadingTables(false);
        setRefreshing(false);
      }
    }
  }, []);

  const tableCountLabel = useMemo(() => {
    return tables.length === 1 ? "1 Table" : `${tables.length} Tables`;
  }, [tables.length]);

  const occupiedCount = useMemo(() => {
    return tables.filter((table) => table.is_occupied).length;
  }, [tables]);

  const unavailableCount = useMemo(() => {
    return tables.filter((table) => table.is_blocked).length;
  }, [tables]);

  return (
    <div className="h-screen overflow-hidden bg-slate-50">
      <div className="mb-4 flex flex-col gap-4 border-b bg-white px-6 py-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">
            Restaurant Floor Plan
          </h1>

          <p className="text-sm text-gray-500">
            Select an available table to start or continue a dine-in order.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-2 rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-gray-700">
            <Armchair size={16} />
            {tableCountLabel}
          </div>

          <div className="rounded-full bg-red-100 px-4 py-2 text-sm font-semibold text-red-700">
            {occupiedCount} Occupied
          </div>

          {unavailableCount > 0 && (
            <div className="rounded-full bg-slate-200 px-4 py-2 text-sm font-semibold text-slate-600">
              {unavailableCount} Unavailable
            </div>
          )}

          <button
            type="button"
            onClick={() => {
              fetchTables();
            }}
            disabled={refreshing}
            className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:opacity-50">
            <RefreshCw
              size={16}
              className={refreshing ? "animate-spin" : ""}
            />

            {refreshing ? "Refreshing" : "Refresh"}
          </button>
        </div>
      </div>

      {error && (
        <div className="mx-6 mb-4 flex items-center gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-red-700">
          <AlertCircle size={20} />

          <p className="text-sm font-semibold">{error}</p>
        </div>
      )}

      <div className="h-[calc(100vh-150px)] overflow-y-auto rounded-xl bg-slate-100 p-6">
        {loadingTables ? (
          <div className="flex h-full items-center justify-center gap-3 text-gray-500">
            <Loader2
              size={24}
              className="animate-spin text-indigo-600"
            />
            Loading floor plan...
          </div>
        ) : (
          <div className="relative min-h-[620px] rounded-3xl border-4 border-slate-300 bg-white p-8 shadow-inner">
            <div className="absolute left-1/2 top-4 -translate-x-1/2 rounded-full bg-slate-200 px-6 py-2 text-xs font-bold uppercase tracking-wider text-slate-600">
              Main Dining Room
            </div>

            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 rounded-full bg-amber-100 px-5 py-2 text-xs font-semibold text-amber-700">
              Entrance
            </div>

            <div className="absolute right-4 top-1/2 -translate-y-1/2 rounded-full bg-blue-100 px-4 py-2 text-xs font-semibold text-blue-700">
              Window Side
            </div>

            <div className="absolute left-4 top-1/2 -translate-y-1/2 rounded-full bg-purple-100 px-4 py-2 text-xs font-semibold text-purple-700">
              Bar Area
            </div>

            {tables.length === 0 ? (
              <div className="flex min-h-[560px] items-center justify-center text-gray-400 italic">
                No tables found. Add them in Tables Management.
              </div>
            ) : (
              <div className="grid min-h-[560px] grid-cols-2 gap-8 pt-16 md:grid-cols-3 lg:grid-cols-4">
                {tables.map((table) => {
                  const capacity = table.display_capacity;

                  const tableShape =
                    capacity >= 6 ? "rounded-2xl" : "rounded-full";

                  const colors = getTableClasses(table);

                  const statusLabel = getStatusLabel(table);

                  const disabled = table.is_blocked;

                  return (
                    <button
                      key={String(table.id)}
                      type="button"
                      disabled={disabled}
                      onClick={() => {
                        if (!disabled) {
                          navigate(
                            `/dashboard/restaurant/dine-in/table/${table.id}`
                          );
                        }
                      }}
                      title={
                        disabled
                          ? `Table is ${statusLabel.toLowerCase()}.`
                          : `Open Table ${table.display_number}`
                      }
                      className={`relative flex min-h-36 flex-col items-center justify-center border-4 p-5 text-center shadow-lg transition ${tableShape} ${
                        colors.border
                      } ${colors.background} ${colors.text} ${
                        disabled
                          ? "cursor-not-allowed opacity-70"
                          : "cursor-pointer hover:scale-105 hover:shadow-xl"
                      }`}>
                      <div className="absolute -top-4 left-1/2 h-7 w-12 -translate-x-1/2 rounded-full bg-slate-300" />

                      <div className="absolute -bottom-4 left-1/2 h-7 w-12 -translate-x-1/2 rounded-full bg-slate-300" />

                      <div className="absolute -left-4 top-1/2 h-12 w-7 -translate-y-1/2 rounded-full bg-slate-300" />

                      <div className="absolute -right-4 top-1/2 h-12 w-7 -translate-y-1/2 rounded-full bg-slate-300" />

                      <div className="text-xl font-black">
                        {table.display_number}
                      </div>

                      <div className="mt-1 text-sm font-semibold opacity-80">
                        {capacity} seats
                      </div>

                      <div
                        className={`mt-3 rounded-full px-3 py-1 text-xs font-bold ${colors.badge}`}>
                        {statusLabel}
                      </div>

                      {table.current_status === "MERGED" && (
                        <div className="mt-2 text-[10px] font-bold uppercase">
                          Managed by another table
                        </div>
                      )}

                      {table.current_status === "NEEDS_CLEANING" && (
                        <div className="mt-2 text-[10px] font-bold uppercase">
                          Staff action required
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
