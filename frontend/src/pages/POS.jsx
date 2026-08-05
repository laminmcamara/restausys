import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import api from "../services/api";

export default function POS() {
  const { tableId } = useParams();

  const [tables, setTables] = useState([]);
  const [activeTable, setActiveTable] = useState(null);

  const [order, setOrder] = useState(null);
  const [menu, setMenu] = useState([]);
  const [loadingOrder, setLoadingOrder] = useState(false);

  const [selectedProduct, setSelectedProduct] = useState(null);
  const [selectedOptions, setSelectedOptions] = useState({});

  const formatMoney = (value) =>
    value !== undefined && value !== null ? Number(value).toFixed(2) : "0.00";

  /* ================= ADD PRODUCT ================= */

  const handleAddProduct = async (product) => {
    if (!order) return;

    if (product.modifier_groups?.length > 0) {
      setSelectedProduct(product);
      setSelectedOptions({});
      return;
    }

    addOrderItem(product, []);
  };

  const addOrderItem = async (product, modifierIds) => {
    try {
      const payload = {
        order: order.id, // ✅ USE REAL ID
        product_id: product.id,
        quantity: 1,
        modifier_ids: modifierIds, // ✅ FIXED FIELD NAME
      };

      await api.post("/order-items/", payload);
      await refreshOrder();
      setSelectedProduct(null);
    } catch (error) {
      console.error("BACKEND ERROR:", error.response?.data);
    }
  };

  /* ================= MODIFIER HANDLING ================= */

  const handleOptionSelect = (group, option) => {
    setSelectedOptions((prev) => {
      const current = prev[group.id] || [];

      if (group.selection_type === "SINGLE") {
        return { ...prev, [group.id]: [option] };
      }

      const exists = current.find((o) => o.id === option.id);

      return {
        ...prev,
        [group.id]: exists
          ? current.filter((o) => o.id !== option.id)
          : [...current, option],
      };
    });
  };

  const confirmModifiers = () => {
    const allSelected = Object.values(selectedOptions)
      .flat()
      .map((opt) => opt.id);

    addOrderItem(selectedProduct, allSelected);
  };

  /* ================= FETCH TABLES ================= */

  useEffect(() => {
    fetchTables();
  }, []);

  const fetchTables = async () => {
    try {
      const res = await api.get("/tables/");
      setTables(res.data.results || res.data);
    } catch (err) {
      console.error(err);
    }
  };

  /* ================= ACTIVE TABLE ================= */

  useEffect(() => {
    if (tableId) {
      setActiveTable(parseInt(tableId));
    }
  }, [tableId]);

  /* ================= OPEN ORDER ================= */

  useEffect(() => {
    if (!activeTable) return;

    const openOrder = async () => {
      try {
        setLoadingOrder(true);
        const res = await api.post("/orders/open_or_create/", {
          table_id: activeTable,
        });
        setOrder(res.data);
      } catch (err) {
        console.error("Error opening order:", err);
      } finally {
        setLoadingOrder(false);
      }
    };

    openOrder();
  }, [activeTable]);

  /* ================= LOAD MENU ================= */

  useEffect(() => {
    const fetchMenu = async () => {
      try {
        const res = await api.get("/products/");
        setMenu(res.data.results || res.data);
      } catch (err) {
        console.error("Error loading menu:", err);
      }
    };

    fetchMenu();
  }, []);

  /* ================= ORDER ACTIONS ================= */

  const refreshOrder = async () => {
    if (!order) return;
    const res = await api.get(`/orders/${order.id}/`); // ✅ REAL ID
    setOrder(res.data);
  };

  const increaseQty = async (item) => {
    await api.patch(`/order-items/${item.id}/`, {
      quantity: item.quantity + 1,
    });
    refreshOrder();
  };

  const decreaseQty = async (item) => {
    if (item.quantity <= 1) return;
    await api.patch(`/order-items/${item.id}/`, {
      quantity: item.quantity - 1,
    });
    refreshOrder();
  };

  const removeItem = async (item) => {
    await api.delete(`/order-items/${item.id}/`);
    refreshOrder();
  };

  const sendToKitchen = async () => {
    await api.post(`/orders/${order.id}/send_to_kitchen/`); // ✅ REAL ID
    refreshOrder();
  };

  const markPaid = async () => {
    await api.post(`/orders/${order.id}/mark_paid/`); // ✅ REAL ID
    setOrder(null);
    setActiveTable(null);
    fetchTables();
  };

  /* ================= UI ================= */

  return (
    <div className="grid grid-cols-5 h-screen">
      {/* LEFT: TABLES */}
      <div className="col-span-1 border-r p-4 overflow-y-auto">
        <h2 className="text-lg font-semibold mb-4">Tables</h2>

        <div className="grid grid-cols-2 gap-3">
          {tables.map((table) => (
            <div
              key={table.id}
              onClick={() => setActiveTable(table.id)}
              className={`p-4 rounded-lg cursor-pointer text-center transition ${
                activeTable === table.id ? "ring-2 ring-blue-500" : ""
              } bg-green-100 text-green-700`}>
              <div className="font-semibold">Table {table.table_number}</div>
            </div>
          ))}
        </div>
      </div>

      {/* MIDDLE: MENU */}
      <div className="col-span-2 border-r p-4 overflow-y-auto">
        <h2 className="text-lg font-semibold mb-4">Menu</h2>

        <div className="grid grid-cols-2 gap-3">
          {menu.map((product) => (
            <button
              key={product.id}
              onClick={() => handleAddProduct(product)}
              className="p-3 bg-gray-100 rounded hover:bg-gray-200 text-left">
              <div className="font-medium">{product.name}</div>
              <div className="text-sm text-gray-500">
                ${formatMoney(product.base_price)}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* RIGHT: ORDER */}
      <div className="col-span-2 p-6 overflow-y-auto">
        {!order ? (
          <div>Select a table to begin.</div>
        ) : (
          <>
            <h2 className="text-xl font-semibold mb-4">
              Order #{order.display_id}
            </h2>

            {order.items?.map((item) => (
              <div
                key={item.id}
                className="bg-gray-100 p-3 rounded mb-3">
                <div className="flex justify-between">
                  <div>{item.product?.name}</div>
                  <button onClick={() => removeItem(item)}>✕</button>
                </div>

                {/* ✅ FIXED MODIFIER FIELD */}
                {item.modifiers?.map((opt) => (
                  <div
                    key={opt.id}
                    className="text-sm text-gray-600">
                    + {opt.name}
                  </div>
                ))}

                <div className="flex justify-between mt-2">
                  <div className="flex gap-2">
                    <button onClick={() => decreaseQty(item)}>-</button>
                    <span>{item.quantity}</span>
                    <button onClick={() => increaseQty(item)}>+</button>
                  </div>

                  <div>${formatMoney(item.final_price)}</div>
                </div>
              </div>
            ))}

            <div className="border-t pt-4 font-bold text-lg flex justify-between">
              <span>Total</span>
              <span>${formatMoney(order.total_price)}</span>
            </div>

            <div className="mt-6 flex gap-3">
              <button
                onClick={sendToKitchen}
                disabled={order.status !== "DRAFT"}
                className={`flex-1 py-2 rounded text-white ${
                  order.status === "DRAFT"
                    ? "bg-orange-600 hover:bg-orange-700"
                    : "bg-gray-400 cursor-not-allowed"
                }`}>
                Send to Kitchen
              </button>

              <button
                onClick={markPaid}
                disabled={
                  order.status !== "IN_PROGRESS" && order.status !== "READY"
                }
                className={`flex-1 py-2 rounded text-white ${
                  order.status === "IN_PROGRESS" || order.status === "READY"
                    ? "bg-green-600 hover:bg-green-700"
                    : "bg-gray-400 cursor-not-allowed"
                }`}>
                Mark Paid
              </button>
            </div>
          </>
        )}
      </div>

      {/* ✅ MODIFIER MODAL */}
      {selectedProduct && (
        <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center">
          <div className="bg-white p-6 rounded w-96">
            <h3 className="text-lg font-semibold mb-4">
              {selectedProduct.name}
            </h3>

            {selectedProduct.modifier_groups.map((group) => (
              <div
                key={group.id}
                className="mb-4">
                <div className="font-medium">{group.name}</div>

                {group.options.map((option) => (
                  <label
                    key={option.id}
                    className="block text-sm">
                    <input
                      type={
                        group.selection_type === "SINGLE" ? "radio" : "checkbox"
                      }
                      name={group.id}
                      onChange={() => handleOptionSelect(group, option)}
                    />
                    {option.name} (+
                    {formatMoney(option.price_adjustment)})
                  </label>
                ))}
              </div>
            ))}

            <div className="flex gap-2 mt-4">
              <button
                onClick={confirmModifiers}
                className="flex-1 bg-blue-600 text-white py-2 rounded">
                Add
              </button>
              <button
                onClick={() => setSelectedProduct(null)}
                className="flex-1 bg-gray-300 py-2 rounded">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
