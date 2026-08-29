import React, { useEffect, useState } from "react";
import api from "../services/api";
import POSProductModal from "./POSProductModal";
import {
  ShoppingCart,
  Trash2,
  ArrowLeft,
  Users,
  Loader2,
  Plus,
  Printer,
  CreditCard,
  Send,
  Utensils,
} from "lucide-react";

export default function POS() {
  const [view, setView] = useState("tables");
  const [selectedTable, setSelectedTable] = useState(null);
  const [activeOrder, setActiveOrder] = useState(null);

  // UI States
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [activeProduct, setActiveProduct] = useState(null);

  // Data States
  const [tables, setTables] = useState([]);
  const [categories, setCategories] = useState([]);
  const [products, setProducts] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);

  // Loading States
  const [loading, setLoading] = useState(true);
  const [issubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    setLoading(true);
    try {
      const [tableRes, catRes, prodRes] = await Promise.all([
        api.get("/tables/"),
        api.get("/manager/categories/"),
        api.get("/manager/products/"),
      ]);
      setTables(tableRes.data.results || tableRes.data);
      setCategories(catRes.data.results || catRes.data);
      setProducts(prodRes.data.results || prodRes.data);
      if (catRes.data.length > 0) setSelectedCategory(catRes.data[0].id);
    } catch (err) {
      console.error("Failed to fetch POS data", err);
    } finally {
      setLoading(false);
    }
  };

  // 1. Open or Create Draft Order when table is clicked
  const handleTableSelect = async (table) => {
    setSelectedTable(table);
    setLoading(true);
    try {
      const res = await api.post("/orders/open_or_create/", {
        table_id: table.id,
      });
      setActiveOrder(res.data);
      setView("menu");
    } catch (err) {
      alert("Could not open table session.");
    } finally {
      setLoading(false);
    }
  };

  // 2. Add Item to Order (Directly to Backend via OrderItemViewSet)
  const addToOrder = async (itemWithModifiers) => {
    setIsSubmitting(true);
    try {
      const payload = {
        order: activeOrder.id,
        product_id: itemWithModifiers.id,
        quantity: itemWithModifiers.quantity,
        modifier_ids: itemWithModifiers.selectedModifiers.map((m) => m.id),
      };
      await api.post("/order-items/", payload);

      // Refresh order to show new items and updated total
      const res = await api.get(`/orders/${activeOrder.id}/`);
      setActiveOrder(res.data);
      setIsModalOpen(false); // Close modal after adding
    } catch (err) {
      alert("Failed to add item.");
    } finally {
      setIsSubmitting(false);
    }
  };

  // 3. Send to Kitchen (Draft -> Placed)
  const handleSendToKitchen = async () => {
    if (!activeOrder || activeOrder.items.length === 0) return;
    setIsSubmitting(true);
    try {
      const res = await api.post(`/orders/${activeOrder.id}/send_to_kitchen/`);
      setActiveOrder(res.data);
      alert("Order sent to kitchen!");
      setView("tables");
      fetchInitialData();
    } catch (err) {
      alert(err.response?.data?.error || "Failed to send to kitchen.");
    } finally {
      setIsSubmitting(false);
    }
  };

  // 4. Mark Paid (Payment)
  const handlePayment = async () => {
    if (!activeOrder) return;
    setIsSubmitting(true);
    try {
      // Note: Using the mark_paid action defined in your OrderViewSet
      await api.post(`/orders/${activeOrder.id}/mark_paid/`, {
        payment_method: "cash",
      });
      alert("Payment Successful!");
      setView("tables");
      fetchInitialData();
    } catch (err) {
      alert("Payment failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const removeItem = async (itemId) => {
    try {
      await api.delete(`/order-items/${itemId}/`);
      const res = await api.get(`/orders/${activeOrder.id}/`);
      setActiveOrder(res.data);
    } catch (err) {
      alert("Cannot remove item.");
    }
  };

  if (loading)
    return (
      <div className="h-screen flex items-center justify-center">
        <Loader2
          className="animate-spin text-blue-600"
          size={40}
        />
      </div>
    );

  if (view === "tables") {
    return (
      <div className="p-6 bg-gray-50 min-h-screen">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-black text-gray-900 mb-6">Floor Plan</h1>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {tables.map((table) => (
              <button
                key={table.id}
                onClick={() => handleTableSelect(table)}
                className={`h-32 rounded-2xl transition-all border-2 flex flex-col items-center justify-center ${
                  table.has_active_session
                    ? "border-orange-400 bg-orange-50"
                    : "border-white bg-white shadow-sm hover:border-blue-400"
                }`}>
                <span className="text-2xl font-black text-gray-800">
                  {table.table_number}
                </span>
                <div className="flex items-center gap-1 text-gray-400 text-xs mt-1">
                  <Users size={14} /> {table.capacity}
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-100 overflow-hidden">
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="bg-white border-b px-4 py-3 flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setView("tables")}
              className="p-2 hover:bg-gray-100 rounded-full">
              <ArrowLeft size={20} />
            </button>
            <div>
              <h2 className="text-lg font-bold leading-tight">
                Table {selectedTable?.table_number}
              </h2>
              <p className="text-xs text-blue-600 font-bold uppercase tracking-tighter">
                {activeOrder?.status}
              </p>
            </div>
          </div>
          <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
            {categories.map((cat) => (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.id)}
                className={`px-4 py-1.5 rounded-full font-bold text-xs whitespace-nowrap transition-all ${
                  selectedCategory === cat.id
                    ? "bg-blue-600 text-white shadow-md"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}>
                {cat.name}
              </button>
            ))}
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-4 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
          {products
            .filter(
              (p) =>
                !selectedCategory ||
                (p.category?.id || p.category) === selectedCategory
            )
            .map((product) => (
              <button
                key={product.id}
                onClick={() => {
                  setActiveProduct(product);
                  setIsModalOpen(true);
                }}
                className="bg-white p-4 rounded-2xl shadow-sm border border-transparent hover:border-blue-500 transition-all text-left flex flex-col justify-between h-36">
                <h3 className="font-bold text-gray-800 text-sm line-clamp-2">
                  {product.name}
                </h3>
                <div className="flex justify-between items-end">
                  <span className="text-lg font-black text-gray-900">
                    ${parseFloat(product.base_price).toFixed(2)}
                  </span>
                  <div className="bg-blue-50 p-1.5 rounded-lg text-blue-600">
                    <Plus size={16} />
                  </div>
                </div>
              </button>
            ))}
        </main>
      </div>

      <aside className="w-80 bg-white border-l flex flex-col shadow-xl">
        <div className="p-4 border-b bg-gray-50/50 flex justify-between items-center">
          <h2 className="text-lg font-bold flex items-center gap-2">
            <ShoppingCart size={18} /> Order Details
          </h2>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {activeOrder?.items?.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-gray-300 italic py-20">
              <Utensils
                size={48}
                className="mb-2 opacity-20"
              />
              <p className="text-sm">No items yet</p>
            </div>
          ) : (
            activeOrder?.items?.map((item) => (
              <div
                key={item.id}
                className="group border-b border-gray-50 pb-2">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <p className="text-sm font-bold text-gray-800 leading-tight">
                      {item.quantity}x {item.product?.name}
                    </p>
                    {item.modifiers?.map((m) => (
                      <p
                        key={m.id}
                        className="text-[10px] text-gray-500 ml-2">
                        • {m.name}
                      </p>
                    ))}
                  </div>
                  <span className="text-sm font-bold text-gray-900 ml-2">
                    ${parseFloat(item.final_price).toFixed(2)}
                  </span>
                </div>
                {activeOrder.status === "DRAFT" && (
                  <button
                    onClick={() => removeItem(item.id)}
                    className="text-red-400 text-[10px] flex items-center gap-1 hover:text-red-600 mt-1">
                    <Trash2 size={10} /> Remove
                  </button>
                )}
              </div>
            ))
          )}
        </div>

        <div className="p-4 bg-gray-50 border-t space-y-3">
          <div className="flex justify-between items-center text-xl font-black">
            <span>Total</span>
            <span className="text-blue-600">
              ${parseFloat(activeOrder?.total_price || 0).toFixed(2)}
            </span>
          </div>

          {activeOrder?.status === "DRAFT" ? (
            <button
              onClick={handleSendToKitchen}
              disabled={issubmitting || activeOrder?.items?.length === 0}
              className="w-full bg-orange-500 text-white py-4 rounded-xl font-bold text-md shadow-lg hover:bg-orange-600 transition-all flex justify-center items-center gap-2">
              {issubmitting ? (
                <Loader2 className="animate-spin" />
              ) : (
                <>
                  <Send size={18} /> Send to Kitchen
                </>
              )}
            </button>
          ) : (
            <div className="grid grid-cols-1 gap-2">
              <button
                onClick={handlePayment}
                disabled={issubmitting}
                className="w-full bg-emerald-600 text-white py-4 rounded-xl font-bold flex justify-center items-center gap-2 shadow-lg hover:bg-emerald-700">
                {issubmitting ? (
                  <Loader2 className="animate-spin" />
                ) : (
                  <>
                    <CreditCard size={18} /> Process Payment
                  </>
                )}
              </button>
              <button className="w-full bg-gray-800 text-white py-3 rounded-xl font-bold flex justify-center items-center gap-2 text-sm">
                <Printer size={16} /> Print Receipt
              </button>
            </div>
          )}
        </div>
      </aside>

      <POSProductModal
        isOpen={isModalOpen}
        product={activeProduct}
        onClose={() => setIsModalOpen(false)}
        onAddToCart={addToOrder}
      />
    </div>
  );
}
