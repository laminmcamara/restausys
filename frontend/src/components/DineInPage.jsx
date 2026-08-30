import React from "react";
import { Users, CheckCircle2, Clock } from "lucide-react";

const DineInPage = ({ floorTables, onSendOrder }) => {
  // Helper to determine status colors
  const getStatusColor = (table) => {
    if (table.has_active_session)
      return "border-orange-500 bg-orange-50 shadow-orange-100";
    return "border-slate-200 bg-white hover:border-indigo-500 hover:shadow-lg hover:shadow-indigo-100";
  };

  return (
    <div className="w-full animate-in fade-in duration-500">
      <header className="mb-6">
        <p className="text-slate-500 font-medium">
          Select an active table to manage or a vacant table to start a new
          order.
        </p>
      </header>

      {/* MAXIMIZED GRID: Auto-scaling columns based on screen width */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-8 gap-6">
        {floorTables.map((table) => (
          <button
            key={table.id}
            onClick={() => onSendOrder({ table: table.id })}
            className={`relative group flex flex-col items-center justify-center p-6 rounded-[32px] border-4 transition-all aspect-square ${getStatusColor(
              table
            )}`}>
            {/* Occupied Badge */}
            {table.has_active_session && (
              <div className="absolute -top-2 -right-2 bg-orange-500 text-white p-1.5 rounded-full shadow-lg animate-pulse">
                <Clock size={14} />
              </div>
            )}

            {/* Table Number/Name - Large and Clear */}
            <span
              className={`text-4xl font-black mb-2 ${
                table.has_active_session ? "text-orange-700" : "text-slate-800"
              }`}>
              {table.table_number || table.name}
            </span>

            {/* Capacity & Status */}
            <div className="flex flex-col items-center gap-1">
              <div className="flex items-center gap-1.5 text-slate-500 font-bold text-xs">
                <Users size={14} />
                {table.capacity} Seats
              </div>

              <span
                className={`text-[10px] font-black uppercase tracking-widest mt-2 px-3 py-1 rounded-full ${
                  table.has_active_session
                    ? "bg-orange-200 text-orange-700"
                    : "bg-slate-100 text-slate-400"
                }`}>
                {table.has_active_session ? "Occupied" : "Available"}
              </span>
            </div>

            {/* Hover Indicator */}
            {!table.has_active_session && (
              <div className="absolute inset-0 flex items-center justify-center bg-indigo-600/90 rounded-[28px] opacity-0 group-hover:opacity-100 transition-opacity">
                <span className="text-white font-black text-sm tracking-tighter">
                  OPEN TABLE
                </span>
              </div>
            )}
          </button>
        ))}
      </div>

      {/* Legend */}
      <div className="mt-12 flex gap-6 border-t border-slate-200 pt-6">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full bg-white border-2 border-slate-200"></div>
          <span className="text-xs font-bold text-slate-500 uppercase">
            Available
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full bg-orange-500"></div>
          <span className="text-xs font-bold text-slate-500 uppercase">
            Occupied / In-Progress
          </span>
        </div>
      </div>
    </div>
  );
};

export default DineInPage;
