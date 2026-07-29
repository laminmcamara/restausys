import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";

export default function POS() {
  const [tables, setTables] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchTables();
  }, []);

  const fetchTables = async () => {
    try {
      const res = await api.get("/tables/");
      setTables(res.data.results || res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // ✅ Numeric sorting
  const sortedTables = [...tables].sort((a, b) => {
    const numA = parseInt(a.table_number.replace(/\D/g, ""));
    const numB = parseInt(b.table_number.replace(/\D/g, ""));
    return numA - numB;
  });

  // ✅ Handle table click
  const handleTableClick = async (table) => {
    try {
      // 1️⃣ Try to find open order for this table
      const res = await api.get(`/orders/?table=${table.id}&status=draft`);

      let order;

      if (res.data.results && res.data.results.length > 0) {
        // ✅ Existing draft order found
        order = res.data.results[0];
      } else {
        // ✅ No draft → create new order
        const createRes = await api.post("/orders/", {
          table: table.id,
        });

        order = createRes.data;
      }

      // ✅ Navigate to order page
      navigate(`/pos/${order.id}`);
    } catch (err) {
      console.error("Error handling table:", err);
    }
  };

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Select Table</h2>

      {loading ? (
        <p>Loading tables...</p>
      ) : (
        <div className="grid grid-cols-6 gap-4 max-h-[500px] overflow-y-auto pr-2">
          {sortedTables.map((table) => (
            <div
              key={table.id}
              onClick={() => handleTableClick(table)}
              className="bg-blue-100 hover:bg-blue-200 cursor-pointer p-4 rounded-lg text-center font-semibold transition"
            >
              Table {table.table_number}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}