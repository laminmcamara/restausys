import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Armchair } from "lucide-react";
import api from "../services/api";

export default function FloorPlan() {
  const navigate = useNavigate();

  const [tables, setTables] = useState([]);
  const [loadingTables, setLoadingTables] = useState(true);

  useEffect(() => {
    fetchTables();
  }, []);

  const fetchTables = async () => {
    try {
      setLoadingTables(true);
    
      const res = await api.get("/tables/");
      setTables(res.data.results || res.data);
    } catch (err) {
      console.error("Failed to load tables:", err);
    } finally {
      setLoadingTables(false);
    }
  };

  const handleTableClick = (table) => {
    navigate(`/dashboard/restaurant/dine-in/table/${table.id}`);
  };

  return (
    <div className="h-screen overflow-hidden">
      <div className="mb-4 flex items-center justify-between border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">
            Restaurant Floor Plan
          </h1>
          <p className="text-sm text-gray-500">
            Select a table to start or continue a dine-in order.
          </p>
        </div>

        <div className="flex items-center gap-2 rounded-full bg-gray-100 px-4 py-2 text-sm font-semibold text-gray-700">
          <Armchair size={16} />
          {tables.length} Tables
        </div>
      </div>

      <div className="h-[calc(100vh-130px)] overflow-y-auto rounded-xl bg-slate-100 p-6">
        {loadingTables ? (
          <div className="flex h-full items-center justify-center text-gray-500">
            Loading floor plan...
          </div>
        ) : (
          <div className="relative min-h-[620px] rounded-3xl border-4 border-slate-300 bg-white p-8 shadow-inner">
            {/* Decorative Zone Labels */}
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
              <div className="flex h-full items-center justify-center text-gray-400 italic">
                No tables found. Add them in Tables Management.
              </div>
            ) : (
              <div className="grid h-full min-h-[560px] grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-8 pt-16">
                {tables.map((table) => {
                  // FIXED: Using has_active_session from your API response
                  const isOccupied = table.has_active_session === true;

                  // Use capacity for shape logic if seats isn't present
                  const capacity = table.capacity || table.seats || 0;
                  const tableShape =
                    capacity >= 6 ? "rounded-2xl" : "rounded-full";

                  return (
                    <button
                      key={table.id}
                      type="button"
                      onClick={() => handleTableClick(table)}
                      className={`relative flex min-h-36 flex-col items-center justify-center border-4 p-5 text-center shadow-lg transition hover:scale-105 ${tableShape} ${
                        isOccupied
                          ? "border-red-300 bg-red-100 text-red-800"
                          : "border-green-300 bg-green-100 text-green-800"
                      }`}>
                      {/* Chair Decorations */}
                      <div className="absolute -top-4 left-1/2 h-7 w-12 -translate-x-1/2 rounded-full bg-slate-300" />
                      <div className="absolute -bottom-4 left-1/2 h-7 w-12 -translate-x-1/2 rounded-full bg-slate-300" />
                      <div className="absolute -left-4 top-1/2 h-12 w-7 -translate-y-1/2 rounded-full bg-slate-300" />
                      <div className="absolute -right-4 top-1/2 h-12 w-7 -translate-y-1/2 rounded-full bg-slate-300" />

                      <div className="text-xl font-black">
                        {table.table_number}
                      </div>

                      <div className="mt-1 text-sm font-semibold opacity-80">
                        {capacity} seats
                      </div>

                      <div className="mt-3 rounded-full bg-white/70 px-3 py-1 text-xs font-bold">
                        {isOccupied ? "Occupied" : "Available"}
                      </div>
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
