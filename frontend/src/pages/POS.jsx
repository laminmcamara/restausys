import React, { useEffect, useState } from "react";
import api from "../services/api";
import POSProductModal from "./POSProductModal";
import TakeOutPage from "../components/TakeOutPage";
import DineInPage from "../components/DineInPage";
import PrintableOrderDocument from "../components/printing/PrintableOrderDocument";
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
  LayoutGrid,
  ShoppingBag,
} from "lucide-react";

export default function POS() {
  const [view, setView] = useState("mode-select");
  const [selectedTable, setSelectedTable] = useState(null);
  const [activeOrder, setActiveOrder] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [activeProduct, setActiveProduct] = useState(null);
  const [showPrintModal, setShowPrintModal] = useState(false);
  const [printData, setPrintData] = useState(null);
  const [printType, setPrintType] = useState("receipt");
  const [tables, setTables] = useState([]);
  const [categories, setCategories] = useState([]);
  const [products, setProducts] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentSession, setCurrentSession] = useState(null);

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    setLoading(true);
    try {
      const [tableRes, catRes, prodRes, sessionRes] = await Promise.all([
        api.get("/tables/"),
        api.get("/manager/categories/"),
        api.get("/manager/products/"),
        api.get("/sessions/active/").catch(() => ({ data: null })), // Fetch active session
      ]);

      setTables(tableRes.data.results || tableRes.data);
      setCategories(catRes.data.results || catRes.data);
      setProducts(prodRes.data.results || prodRes.data);
      setCurrentSession(sessionRes.data);

      if (catRes.data.length > 0) setSelectedCategory(catRes.data[0].id);
    } catch (err) {
      console.error("Failed to fetch POS data", err);
    } finally {
      setLoading(false);
    }
  };

  const triggerPrint = (order, type = "receipt") => {
    setPrintData(order);
    setPrintType(type);
    setShowPrintModal(true);
  };

  const handleTableSelect = async (tableId) => {
    setLoading(true);
    try {
      const res = await api.post("/orders/open_or_create/", {
        table_id: tableId,
      });
      setActiveOrder(res.data);
      setSelectedTable(tables.find((t) => t.id === tableId));
      setView("menu");
    } catch (err) {
      alert("Could not open table session.");
    } finally {
      setLoading(false);
    }
  };

  const handleTakeOutOrder = async (payload) => {
    setIsSubmitting(true);
    try {
      // FIX: Inject the active session ID into the payload
      // If no session exists, we might need to create one or alert the user
      const session_id = currentSession?.id;

      if (!session_id) {
        alert(
          "No active register session found. Please open a session in Settings first."
        );
        setIsSubmitting(false);
        return;
      }

      const formattedPayload = {
        ...payload,
        session: session_id, // This fixes the NOT NULL constraint
        table: null,
        status: "PLACED",
      };

      const res = await api.post("/orders/", formattedPayload);
      triggerPrint(res.data, "kitchen");
      await fetchInitialData();
      setView("mode-select");
      return res.data;
    } catch (err) {
      console.error("Takeout Error:", err.response?.data);
      alert("Failed to create take-out order. Check if a session is open.");
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  };

  const addToOrder = async (itemWithModifiers) => {
    setIsSubmitting(true);
    try {
      const payload = {
        order: activeOrder.id,
        product: itemWithModifiers.id,
        quantity: itemWithModifiers.quantity,
        modifier_ids: itemWithModifiers.selectedModifiers.map((m) => m.id),
      };
      await api.post("/order-items/", payload);
      const res = await api.get(`/orders/${activeOrder.id}/`);
      setActiveOrder(res.data);
      setIsModalOpen(false);
    } catch (err) {
      alert("Failed to add item.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSendToKitchen = async () => {
    if (!activeOrder || activeOrder.items.length === 0) return;
    setIsSubmitting(true);
    try {
      const res = await api.post(`/orders/${activeOrder.id}/send_to_kitchen/`);
      setActiveOrder(res.data);
      triggerPrint(res.data, "kitchen");
      setView("mode-select");
      fetchInitialData();
    } catch (err) {
      alert("Failed to send to kitchen.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePayment = async () => {
    if (!activeOrder) return;
    setIsSubmitting(true);
    try {
      const res = await api.post(`/orders/${activeOrder.id}/mark_paid/`, {
        payment_method: "cash",
      });
      triggerPrint(res.data, "receipt");
      setView("mode-select");
      fetchInitialData();
    } catch (err) {
      alert("Payment failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading)
    return (
      <div className="h-screen flex items-center justify-center bg-slate-50">
        <Loader2
          className="animate-spin text-indigo-600"
          size={40}
        />
      </div>
    );

  if (view === "mode-select") {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6 text-center">
        <div className="max-w-4xl w-full">
          {!currentSession && (
            <div className="mb-8 p-4 bg-red-50 border border-red-200 text-red-700 rounded-2xl font-bold">
              ⚠️ No Active Session. Please open a register session in Settings
              to place orders.
            </div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <button
              onClick={() => setView("dine-in")}
              disabled={!currentSession}
              className="group bg-white p-12 rounded-[40px] shadow-xl border-4 border-transparent hover:border-indigo-600 transition-all flex flex-col items-center disabled:opacity-50 disabled:hover:border-transparent">
              <div className="w-24 h-24 bg-indigo-100 rounded-3xl flex items-center justify-center text-indigo-600 mb-6 group-hover:scale-110 transition-transform">
                <LayoutGrid size={48} />
              </div>
              <h2 className="text-3xl font-black text-slate-900 mb-2">
                Dine-In
              </h2>
              <p className="text-slate-500 font-medium">
                Manage tables and floor plan
              </p>
            </button>
            <button
              onClick={() => setView("take-out")}
              disabled={!currentSession}
              className="group bg-white p-12 rounded-[40px] shadow-xl border-4 border-transparent hover:border-orange-500 transition-all flex flex-col items-center disabled:opacity-50 disabled:hover:border-transparent">
              <div className="w-24 h-24 bg-orange-100 rounded-3xl flex items-center justify-center text-orange-600 mb-6 group-hover:scale-110 transition-transform">
                <ShoppingBag size={48} />
              </div>
              <h2 className="text-3xl font-black text-slate-900 mb-2">
                Take-Out
              </h2>
              <p className="text-slate-500 font-medium">Quick walk-in orders</p>
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (view === "dine-in") {
    return (
      <div className="p-6 bg-slate-50 min-h-screen">
        <div className="max-w-[1800px] mx-auto">
          <div className="flex items-center gap-4 mb-8">
            <button
              onClick={() => setView("mode-select")}
              className="p-3 bg-white rounded-2xl shadow-sm hover:bg-slate-100 transition-colors">
              <ArrowLeft size={24} />
            </button>
            <h1 className="text-3xl font-black text-slate-900">Floor Plan</h1>
          </div>
          <DineInPage
            floorTables={tables}
            products={products}
            onSendOrder={(payload) => handleTableSelect(payload.table)}
          />
        </div>
      </div>
    );
  }

  if (view === "take-out") {
    return (
      <div className="p-6 bg-slate-50 min-h-screen">
        <div className="max-w-[1800px] mx-auto">
          <div className="flex items-center gap-4 mb-8">
            <button
              onClick={() => setView("mode-select")}
              className="p-3 bg-white rounded-2xl shadow-sm hover:bg-slate-100 transition-colors">
              <ArrowLeft size={24} />
            </button>
            <h1 className="text-3xl font-black text-slate-900">
              Take-Out Order
            </h1>
          </div>
          <TakeOutPage
            products={products}
            onSendOrder={handleTakeOutOrder}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-slate-100 overflow-hidden">
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="bg-white border-b px-6 py-3 flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setView("dine-in")}
              className="p-2 hover:bg-slate-100 rounded-xl transition-colors">
              <ArrowLeft size={20} />
            </button>
            <div>
              <h2 className="text-lg font-black text-slate-900 leading-tight">
                Table {selectedTable?.table_number}
              </h2>
              <span className="text-[9px] font-black uppercase tracking-widest text-indigo-600">
                {activeOrder?.status}
              </span>
            </div>
          </div>
          <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide max-w-3xl">
            {categories.map((cat) => (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.id)}
                className={`px-4 py-1.5 rounded-lg font-bold text-[11px] whitespace-nowrap transition-all ${
                  selectedCategory === cat.id
                    ? "bg-indigo-600 text-white shadow-md shadow-indigo-100"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}>
                {cat.name}
              </button>
            ))}
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-4 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-7 gap-3">
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
                className="bg-white p-3 rounded-2xl shadow-sm border border-slate-100 hover:border-indigo-500 hover:shadow-md transition-all text-left flex flex-col justify-between min-h-[120px] active:scale-95">
                <h3 className="font-bold text-slate-800 text-[13px] leading-snug break-words line-clamp-3">
                  {product.name}
                </h3>
                <div className="flex justify-between items-center mt-2 pt-2 border-t border-slate-50">
                  <span className="text-sm font-black text-indigo-600">
                    ${parseFloat(product.base_price).toFixed(2)}
                  </span>
                  <Plus
                    size={14}
                    className="text-slate-300"
                  />
                </div>
              </button>
            ))}
        </main>
      </div>

      <aside className="w-60 bg-white border-l flex flex-col shadow-2xl z-10">
        <div className="p-3 border-b bg-slate-50 flex justify-between items-center">
          <h2 className="text-xs font-black text-slate-900 flex items-center gap-1.5 uppercase tracking-tighter">
            <ShoppingCart size={14} /> Cart
          </h2>
          <span className="text-[9px] font-mono text-slate-400">
            #{activeOrder?.display_id}
          </span>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {activeOrder?.items?.map((item) => (
            <div
              key={item.id}
              className="group border-b border-slate-50 pb-2">
              <div className="flex justify-between items-start gap-2">
                <div className="flex-1 min-w-0">
                  <p className="text-[11px] font-bold text-slate-800 leading-tight truncate">
                    {item.quantity}x {item.product?.name}
                  </p>
                </div>
                <span className="text-[11px] font-black text-slate-900 whitespace-nowrap">
                  ${parseFloat(item.final_price).toFixed(2)}
                </span>
              </div>
            </div>
          ))}
        </div>

        <div className="p-3 bg-slate-900 text-white">
          <div className="flex justify-between items-center mb-3">
            <span className="text-slate-400 text-[9px] font-bold uppercase">
              Total
            </span>
            <span className="text-xl font-black">
              ${parseFloat(activeOrder?.total_price || 0).toFixed(2)}
            </span>
          </div>
          <button
            onClick={handleSendToKitchen}
            className="w-full bg-indigo-600 text-white py-3 rounded-lg font-black text-xs">
            KITCHEN
          </button>
        </div>
      </aside>

      <POSProductModal
        isOpen={isModalOpen}
        product={activeProduct}
        onClose={() => setIsModalOpen(false)}
        onAddToCart={addToOrder}
      />
      {showPrintModal && (
        <div className="fixed inset-0 z-[999] bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-8 max-w-sm w-full shadow-2xl text-center">
            <h3 className="text-xl font-black text-slate-900">
              Printing {printType}...
            </h3>
            <div className="hidden">
              <PrintableOrderDocument
                order={printData}
                type={printType}
              />
            </div>
            <button
              onClick={() => setShowPrintModal(false)}
              className="mt-6 w-full bg-slate-900 text-white py-4 rounded-2xl font-black">
              DONE
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
