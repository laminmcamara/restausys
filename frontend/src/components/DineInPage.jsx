import React from "react";
import { Users, Clock, Utensils, ChevronRight } from "lucide-react";

// Changed prop name to onTableSelect to match POS.jsx
const DineInPage = ({ floorTables, onTableSelect }) => {
  // Helper to determine if a table is occupied
  const isOccupied = (table) => {
    return (
      table.has_active_session ||
      table.is_occupied ||
      table.current_order ||
      table.status === "OCCUPIED"
    );
  };

  // Helper to determine status colors
  const getStatusColor = (table) => {
    if (isOccupied(table))
      return "border-orange-500 bg-orange-50 shadow-orange-100";
    return "border-slate-200 bg-white hover:border-indigo-500 hover:shadow-lg hover:shadow-indigo-100";
  };

  return (
    <div className="flex flex-col h-full max-h-screen animate-in fade-in duration-500 p-4">
      {/* Compact Header */}
      <header className="mb-4 flex items-center justify-between flex-shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <Utensils
              className="text-indigo-600"
              size={20}
            />
            <h2 className="text-xl font-black text-slate-800 tracking-tight">
              Floor Map
            </h2>
          </div>
          <p className="text-slate-500 text-xs font-medium">
            Select a table to begin
          </p>
        </div>

        <div className="flex gap-3 bg-slate-100 p-1 rounded-xl">
          <div className="flex items-center gap-1.5 px-3 py-1 bg-white rounded-lg shadow-sm">
            <div className="w-2 h-2 rounded-full bg-slate-300"></div>
            <span className="text-[10px] font-black text-slate-500 uppercase">
              Vacant
            </span>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1">
            <div className="w-2 h-2 rounded-full bg-orange-500 animate-pulse"></div>
            <span className="text-[10px] font-black text-slate-500 uppercase">
              Occupied
            </span>
          </div>
        </div>
      </header>

      {/* The Grid: Constrained and Scrollable */}
      <div className="flex-grow overflow-y-auto pr-2 custom-scrollbar">
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-8 gap-3 pb-8">
          {floorTables.map((table) => {
            const occupied = isOccupied(table);
            return (
              <button
                key={table.id}
                // FIX: Pass the whole table object directly to match POS.jsx handleTableSelect(table)
                onClick={() => onTableSelect(table)}
                className={`relative group flex flex-col items-center justify-between p-4 rounded-[24px] border-2 transition-all aspect-square max-h-[140px] ${getStatusColor(
                  table
                )}`}>
                {/* Top Row: Capacity & Status */}
                <div className="w-full flex justify-between items-start">
                  <div className="flex items-center gap-1 text-slate-400 font-bold text-[10px]">
                    <Users size={10} />
                    {table.capacity || 2}
                  </div>
                  {occupied && (
                    <Clock
                      size={12}
                      className="text-orange-500"
                    />
                  )}
                </div>

                {/* Center: Table Number */}
                <span
                  className={`text-3xl font-black leading-none ${
                    occupied ? "text-orange-700" : "text-slate-800"
                  }`}>
                  {table.table_number || table.name}
                </span>

                {/* Bottom: Label */}
                <div className="w-full flex justify-center">
                  <span
                    className={`text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-md ${
                      occupied
                        ? "bg-orange-200 text-orange-700"
                        : "bg-slate-100 text-slate-400"
                    }`}>
                    {occupied ? "In Use" : "Open"}
                  </span>
                </div>

                {/* Hover Overlay */}
                {!occupied && (
                  <div className="absolute inset-0 flex items-center justify-center bg-indigo-600/90 rounded-[22px] opacity-0 group-hover:opacity-100 transition-opacity">
                    <ChevronRight
                      className="text-white"
                      size={24}
                    />
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default DineInPage;
