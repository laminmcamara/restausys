import React from "react";

import { ChevronRight, Clock, Utensils, Users } from "lucide-react";

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
  const status = table?.current_status ?? table?.status ?? "AVAILABLE";

  const normalizedStatus = normalizeTableStatus(status);

  const blockedStatuses = ["NEEDS_CLEANING", "MERGED", "INACTIVE"];

  const isOccupied =
    Boolean(table?.is_occupied) ||
    Boolean(table?.has_active_session) ||
    Boolean(table?.current_order) ||
    normalizedStatus === "OCCUPIED";

  const isBlocked = blockedStatuses.includes(normalizedStatus);

  const capacity = Number(table?.capacity ?? table?.seats ?? 0);

  return {
    ...table,
    status: normalizedStatus,
    current_status: normalizedStatus,
    is_occupied: isOccupied,
    is_blocked: isBlocked,
    is_available: table?.is_available !== false && !isBlocked,
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
    return "In Use";
  }

  return "Open";
};

const getStatusColor = (table) => {
  if (table.is_blocked) {
    return "border-slate-300 bg-slate-200 text-slate-500";
  }

  if (table.is_occupied) {
    return "border-orange-500 bg-orange-50 text-orange-800 shadow-orange-100";
  }

  return "border-slate-200 bg-white text-slate-800 hover:border-indigo-500 hover:shadow-lg hover:shadow-indigo-100";
};

const getStatusBadgeColor = (table) => {
  if (table.is_blocked) {
    return "bg-slate-400 text-white";
  }

  if (table.is_occupied) {
    return "bg-orange-200 text-orange-700";
  }

  return "bg-slate-100 text-slate-500";
};

const DineInPage = ({ floorTables = [], onTableSelect }) => {
  const normalizedTables = Array.isArray(floorTables)
    ? floorTables.map(normalizeTable)
    : [];

  return (
    <div className="flex h-full max-h-screen flex-col animate-in fade-in duration-500 p-4">
      <header className="mb-4 flex flex-shrink-0 items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Utensils
              className="text-indigo-600"
              size={20}
            />

            <h2 className="text-xl font-black tracking-tight text-slate-800">
              Floor Map
            </h2>
          </div>

          <p className="text-xs font-medium text-slate-500">
            Select a table to begin or continue a dine-in order.
          </p>
        </div>

        <div className="flex gap-3 rounded-xl bg-slate-100 p-1">
          <div className="flex items-center gap-1.5 rounded-lg bg-white px-3 py-1 shadow-sm">
            <div className="h-2 w-2 rounded-full bg-slate-300" />

            <span className="text-[10px] font-black uppercase text-slate-500">
              Open
            </span>
          </div>

          <div className="flex items-center gap-1.5 px-3 py-1">
            <div className="h-2 w-2 animate-pulse rounded-full bg-orange-500" />

            <span className="text-[10px] font-black uppercase text-slate-500">
              In Use
            </span>
          </div>
        </div>
      </header>

      <div className="custom-scrollbar flex-grow overflow-y-auto pr-2">
        {normalizedTables.length === 0 ? (
          <div className="flex min-h-[300px] items-center justify-center rounded-3xl border-2 border-dashed border-slate-200 bg-white text-sm font-bold text-slate-400">
            No tables found.
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3 pb-8 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-8">
            {normalizedTables.map((table) => {
              const statusLabel = getStatusLabel(table);

              const statusColor = getStatusColor(table);

              const badgeColor = getStatusBadgeColor(table);

              const disabled = table.is_blocked;

              return (
                <button
                  key={String(table.id)}
                  type="button"
                  disabled={disabled}
                  onClick={() => {
                    if (!disabled && typeof onTableSelect === "function") {
                      onTableSelect(table);
                    }
                  }}
                  title={
                    disabled
                      ? `Table is ${statusLabel.toLowerCase()}.`
                      : `Open Table ${table.display_number}`
                  }
                  className={`group relative flex aspect-square min-h-[140px] max-h-[160px] flex-col items-center justify-between rounded-[24px] border-2 p-4 text-center transition-all ${statusColor} ${
                    disabled
                      ? "cursor-not-allowed opacity-70"
                      : "cursor-pointer hover:scale-[1.02]"
                  }`}>
                  <div className="flex w-full items-start justify-between">
                    <div className="flex items-center gap-1 text-[10px] font-bold text-slate-400">
                      <Users size={10} />

                      {table.display_capacity || 2}
                    </div>

                    {table.is_occupied && !disabled && (
                      <Clock
                        size={12}
                        className="text-orange-500"
                      />
                    )}
                  </div>

                  <span className="text-3xl font-black leading-none">
                    {table.display_number}
                  </span>

                  <div className="flex w-full justify-center">
                    <span
                      className={`rounded-md px-2 py-0.5 text-[9px] font-black uppercase tracking-widest ${badgeColor}`}>
                      {statusLabel}
                    </span>
                  </div>

                  {!disabled && (
                    <div className="absolute inset-0 flex items-center justify-center rounded-[22px] bg-indigo-600/90 opacity-0 transition-opacity group-hover:opacity-100">
                      <div className="flex items-center gap-2 text-sm font-black uppercase tracking-wide text-white">
                        {table.is_occupied ? "Continue" : "Open"}

                        <ChevronRight size={20} />
                      </div>
                    </div>
                  )}

                  {table.current_status === "MERGED" && (
                    <div className="mt-1 text-[9px] font-bold uppercase text-slate-500">
                      Managed by another table
                    </div>
                  )}

                  {table.current_status === "NEEDS_CLEANING" && (
                    <div className="mt-1 text-[9px] font-bold uppercase text-slate-500">
                      Staff action required
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default DineInPage;
