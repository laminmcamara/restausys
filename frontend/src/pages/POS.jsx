import React, { useEffect, useState } from "react";
import api from "../services/api";
import POSProductModal from "./POSProductModal";
import PaymentModal from "./PaymentModal";
import TakeOutPage from "../components/TakeOutPage";
import DineInPage from "../components/DineInPage";
import PrintableOrderDocument from "../components/printing/PrintableOrderDocument";
import {
  ShoppingCart,
  ArrowLeft,
  Loader2,
  Plus,
  LayoutGrid,
  ShoppingBag,
  X,
} from "lucide-react";

export default function POS() {
  const toast = {
    success: (msg) => alert("SUCCESS: " + msg),
    error: (msg) => alert("ERROR: " + msg),
  };

  // --- View & Selection State ---
  const [view, setView] = useState("mode-select"); // mode-select, dine-in, take-out, menu
  const [selectedTable, setSelectedTable] = useState(null);
  const [activeOrder, setActiveOrder] = useState(null);
  const [activeProduct, setActiveProduct] = useState(null);
  const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);
  const [paymentMethods, setPaymentMethods] = useState([]);

  // --- UI State ---
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [showPrintModal, setShowPrintModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // --- Data State ---
  const [tables, setTables] = useState([]);
  const [categories, setCategories] = useState([]);
  const [products, setProducts] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [currentSession, setCurrentSession] = useState(null);

  // --- Printing State ---
  const [printData, setPrintData] = useState(null);
  const [printType, setPrintType] = useState("receipt");

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
        api.get("/sessions/active/").catch(() => ({ data: null })),
      ]);

      setTables(tableRes.data.results || tableRes.data);
      setCategories(catRes.data.results || catRes.data);
      setProducts(prodRes.data.results || prodRes.data);
      setCurrentSession(sessionRes.data);

      if (catRes.data.length > 0) setSelectedCategory(catRes.data[0].id);
    } catch (err) {
      console.error("Failed to fetch POS data", err);
      toast.error("Failed to load POS data");
    } finally {
      setLoading(false);
    }
  };

  /* ================= DINE-IN LOGIC ================= */
  const handleTableSelect = async (table) => {
    setLoading(true);
    try {
      setSelectedTable(table);
      const response = await api.post("/orders/open_or_create/", {
        table: table.id,
        session: currentSession?.id,
      });
      setActiveOrder(response.data);
      setView("menu");
    } catch (err) {
      console.error("Table Select Error:", err);
      toast.error("Could not open table");
    } finally {
      setLoading(false);
    }
  };

  /* ================= ORDER ACTIONS ================= */

  const addToOrder = async (itemData) => {
    if (!activeOrder || !activeOrder.id) {
      toast.error("No active order found");
      return;
    }

    setIsSubmitting(true);
    try {
      // Use standard endpoint with explicit order ID to avoid 404/400 errors
      const payload = {
        order: activeOrder.id,
        product: itemData.product,
        quantity: itemData.quantity,
        final_price: itemData.final_price,
        modifiers: itemData.modifiers || [],
      };

      // 1. Create the item
      await api.post("/order-items/", payload);

      // 2. Fetch the full updated order (to get new total_price and item list)
      const response = await api.get(`/orders/${activeOrder.id}/`);

      setActiveOrder(response.data);
      setIsModalOpen(false);
      toast.success("Item added");
    } catch (err) {
      console.error("Add Item Error:", err.response?.data);
      toast.error("Failed to add item: " + JSON.stringify(err.response?.data));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSendToKitchen = async () => {
    if (!activeOrder || !activeOrder.items?.length) {
      toast.error("Cannot send an empty order to kitchen");
      return;
    }

    setIsSubmitting(true);
    try {
      // Update status to PLACED
      const response = await api.patch(`/orders/${activeOrder.id}/`, {
        status: "PLACED",
      });

      setActiveOrder(response.data);
      toast.success("Order sent to kitchen!");

      // Optional: Go back to floor plan after sending to kitchen
      // setView("dine-in");
    } catch (err) {
      console.error("Kitchen Error:", err.response?.data);
      toast.error("Kitchen Error: " + JSON.stringify(err.response?.data));
    } finally {
      setIsSubmitting(false);
    }
  };

  /* ================= PAYMENT LOGIC ================= */
  const handlePayment = () => {
    if (!activeOrder || activeOrder.items.length === 0) {
      toast.error("Cannot pay for an empty order");
      return;
    }
    setIsPaymentModalOpen(true);
  };

  const fetchPaymentMethods = async () => {
    try {
      const res = await api.get("/payment-methods/");
      // Handle both paginated and non-paginated responses
      const data = res.data.results || res.data;
      setPaymentMethods(data);
      console.log("Loaded Payment Methods:", data);
    } catch (err) {
      console.error("Error fetching payment methods:", err);
      toast.error("Could not load payment methods");
    }
  };
  fetchPaymentMethods();

  const handlePaymentComplete = async (orderId, methodId) => {
    console.log("PAYMENT START:", { orderId, methodId }); // Add this!
    try {
      const payload = {
        order: orderId,
        // Use the price from the order object passed in or the active state
        amount: activeOrder?.total_price || activeOrder?.total_amount || 0,
        method: methodId,
        status: "PAID",
      };

      const res = await api.post("/payments/", payload);
      console.log("PAYMENT SUCCESS:", res.data);

      toast.success("Payment successful!");
      setIsPaymentModalOpen(false);
      setActiveOrder(null);
      setView("mode-select");
    } catch (err) {
      console.error("PAYMENT FAIL:", err.response?.data);
      toast.error("Payment failed");
    }
  };

  /* ================= TAKE-OUT LOGIC ================= */
  const handleTakeOutOrder = async (takeOutCart, customerInfo = {}) => {
    if (!takeOutCart || takeOutCart.length === 0) {
      alert("Cart is empty");
      return;
    }

    setLoading(true);
    try {
      const payload = {
        order_type: "TAKEOUT",
        status: "PLACED",
        session: currentSession?.id,
        customer_name: customerInfo.customer_name || "Walk-in",
        items: takeOutCart.map((item) => ({
          product: item.id,
          quantity: item.quantity,
          final_price: parseFloat(item.price || item.base_price || 0),
          modifiers: item.selectedModifiers?.map((m) => m.id) || [],
        })),
      };

      const response = await api.post("/orders/", payload);

      // For Take-out, we immediately offer payment
      setActiveOrder(response.data);
      setIsPaymentModalOpen(true);

      toast.success("Take-out order created!");
    } catch (error) {
      console.error("Take-out failed:", error.response?.data);
      alert("Order Failed");
    } finally {
      setLoading(false);
    }
  };

  /* ================= VIEW RENDERING ================= */

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-50">
        <Loader2
          className="animate-spin text-indigo-600"
          size={48}
        />
      </div>
    );
  }

  const renderContent = () => {
    // 1. MODE SELECTION
    if (view === "mode-select") {
      return (
        <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6 text-center">
          <div className="max-w-4xl w-full">
            {!currentSession && (
              <div className="mb-8 p-4 bg-red-50 border border-red-200 text-red-700 rounded-2xl font-bold">
                ⚠️ No Active Session. Open register in Settings.
              </div>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <button
                onClick={() => setView("dine-in")}
                disabled={!currentSession}
                className="group bg-white p-12 rounded-[40px] shadow-xl border-4 border-transparent hover:border-indigo-600 transition-all flex flex-col items-center disabled:opacity-50">
                <div className="w-24 h-24 bg-indigo-100 rounded-3xl flex items-center justify-center text-indigo-600 mb-6 group-hover:scale-110 transition-transform">
                  <LayoutGrid size={48} />
                </div>
                <h2 className="text-3xl font-black text-slate-900 mb-2">
                  Dine-In
                </h2>
                <p className="text-slate-500 font-medium">Manage tables</p>
              </button>
              <button
                onClick={() => setView("take-out")}
                disabled={!currentSession}
                className="group bg-white p-12 rounded-[40px] shadow-xl border-4 border-transparent hover:border-orange-500 transition-all flex flex-col items-center disabled:opacity-50">
                <div className="w-24 h-24 bg-orange-100 rounded-3xl flex items-center justify-center text-orange-600 mb-6 group-hover:scale-110 transition-transform">
                  <ShoppingBag size={48} />
                </div>
                <h2 className="text-3xl font-black text-slate-900 mb-2">
                  Take-Out
                </h2>
                <p className="text-slate-500 font-medium">Quick orders</p>
              </button>
            </div>
          </div>
        </div>
      );
    }

    // 2. FLOOR PLAN
    if (view === "dine-in") {
      return (
        <div className="p-6 bg-slate-50 min-h-screen">
          <div className="max-w-[1800px] mx-auto">
            <div className="flex items-center gap-4 mb-8">
              <button
                onClick={() => setView("mode-select")}
                className="p-3 bg-white rounded-2xl shadow-sm hover:bg-slate-100">
                <ArrowLeft size={24} />
              </button>
              <h1 className="text-3xl font-black text-slate-900">Floor Plan</h1>
            </div>
            <DineInPage
              floorTables={tables}
              onTableSelect={handleTableSelect}
            />
          </div>
        </div>
      );
    }

    // 3. TAKE-OUT
    if (view === "take-out") {
      return (
        <div className="p-6 bg-slate-50 min-h-screen">
          <div className="max-w-[1800px] mx-auto">
            <div className="flex items-center gap-4 mb-8">
              <button
                onClick={() => setView("mode-select")}
                className="p-3 bg-white rounded-2xl shadow-sm hover:bg-slate-100">
                <ArrowLeft size={24} />
              </button>
              <h1 className="text-3xl font-black text-slate-900">Take-Out</h1>
            </div>
            <TakeOutPage
              products={products}
              onSendOrder={handleTakeOutOrder}
            />
          </div>
        </div>
      );
    }

    // 4. MENU (Dine-in Order Entry)
    if (view === "menu") {
      return (
        <div className="flex h-screen bg-slate-100 overflow-hidden">
          <div className="flex-1 flex flex-col overflow-hidden">
            <header className="bg-white border-b px-6 py-3 flex items-center justify-between shadow-sm">
              <div className="flex items-center gap-4">
                <button
                  onClick={() => setView("dine-in")}
                  className="p-2 hover:bg-slate-100 rounded-xl">
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
                        ? "bg-indigo-600 text-white shadow-md"
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
                    className="bg-white p-3 rounded-2xl shadow-sm border border-slate-100 hover:border-indigo-500 transition-all text-left flex flex-col justify-between min-h-[120px]">
                    <h3 className="font-bold text-slate-800 text-[13px] line-clamp-3">
                      {product.name}
                    </h3>
                    <div className="flex justify-between items-center mt-2 pt-2 border-t border-slate-50">
                      <span className="text-sm font-black text-indigo-600">
                        $
                        {parseFloat(
                          product.price || product.base_price || 0
                        ).toFixed(2)}
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

          <aside className="w-80 bg-white border-l flex flex-col shadow-2xl z-10">
            <div className="p-4 border-b bg-slate-50 flex justify-between items-center">
              <h2 className="text-xs font-black text-slate-900 flex items-center gap-1.5 uppercase tracking-tighter">
                <ShoppingCart size={14} /> Cart
              </h2>
              <span className="text-[9px] font-mono text-slate-400">
                #{activeOrder?.id?.slice(0, 8)}
              </span>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {activeOrder?.items?.map((item) => (
                <div
                  key={item.id}
                  className="group border-b border-slate-50 pb-3">
                  <div className="flex justify-between items-start gap-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-[12px] font-bold text-slate-800 leading-tight">
                        {item.quantity}x {item.product_name}
                      </p>
                      {item.modifiers?.length > 0 && (
                        <p className="text-[10px] text-slate-400 mt-1">
                          + {item.modifiers.length} modifiers
                        </p>
                      )}
                    </div>
                    <span className="text-[12px] font-black text-slate-900">
                      ${parseFloat(item.total_price || 0).toFixed(2)}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            <div className="p-4 bg-slate-900 text-white">
              <div className="flex justify-between items-center mb-4">
                <span className="text-slate-400 text-[10px] font-bold uppercase tracking-widest">
                  Total
                </span>
                <span className="text-2xl font-black">
                  ${parseFloat(activeOrder?.total_price || 0).toFixed(2)}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={handleSendToKitchen}
                  disabled={isSubmitting || !activeOrder?.items?.length}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white py-4 rounded-xl font-black text-[11px] uppercase tracking-widest transition-colors disabled:opacity-50">
                  Kitchen
                </button>
                <button
                  onClick={handlePayment}
                  disabled={isSubmitting || !activeOrder?.items?.length}
                  className="bg-green-600 hover:bg-green-700 text-white py-4 rounded-xl font-black text-[11px] uppercase tracking-widest transition-colors disabled:opacity-50">
                  Pay
                </button>
              </div>
            </div>
          </aside>
        </div>
      );
    }
  };

  return (
    <>
      {renderContent()}

      {/* GLOBAL MODALS */}
      <POSProductModal
        isOpen={isModalOpen}
        product={activeProduct}
        onClose={() => setIsModalOpen(false)}
        onAddToCart={addToOrder}
      />

      <PaymentModal
        isOpen={isPaymentModalOpen}
        order={activeOrder}
        methods={paymentMethods}
        onClose={() => setIsPaymentModalOpen(false)}
        onPaymentComplete={handlePaymentComplete}
      />

      {showPrintModal && (
        <div className="fixed inset-0 z-[999] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-[32px] p-8 max-w-sm w-full shadow-2xl text-center relative">
            <button
              onClick={() => setShowPrintModal(false)}
              className="absolute top-4 right-4 p-2 hover:bg-slate-100 rounded-full">
              <X size={20} />
            </button>
            <div className="w-20 h-20 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-6">
              <Plus
                size={40}
                className="rotate-45"
              />
            </div>
            <h3 className="text-2xl font-black text-slate-900 mb-2">
              Order Placed!
            </h3>
            <div className="hidden">
              <PrintableOrderDocument
                order={printData}
                type={printType}
              />
            </div>
            <button
              onClick={() => setShowPrintModal(false)}
              className="w-full bg-slate-900 hover:bg-black text-white py-4 rounded-2xl font-black transition-all">
              CONTINUE
            </button>
          </div>
        </div>
      )}
    </>
  );
}
