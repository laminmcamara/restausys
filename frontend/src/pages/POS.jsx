import React, { useCallback, useEffect, useMemo, useState } from "react";

import api from "../services/api";

import POSProductModal from "./POSProductModal";
import PaymentModal from "./PaymentModal";
import TakeOutPage from "../components/TakeOutPage";
import DineInPage from "../components/DineInPage";
import PrintableOrderDocument from "../components/printing/PrintableOrderDocument";

import {
  ArrowLeft,
  LayoutGrid,
  Loader2,
  Plus,
  ShoppingBag,
  ShoppingCart,
  X,
} from "lucide-react";

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

const isCanceledRequest = (error) => {
  return (
    error?.code === "ERR_CANCELED" ||
    error?.name === "CanceledError" ||
    error?.name === "AbortError"
  );
};

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

const getOrderTotal = (order) => {
  return Number(order?.total ?? order?.total_price ?? order?.total_amount ?? 0);
};

const normalizePaymentMethod = (method) => {
  const value = String(method || "")
    .trim()
    .toLowerCase()
    .replaceAll("_", " ")
    .replaceAll("-", " ");

  if (value.includes("cash")) {
    return "cash";
  }

  if (
    value.includes("card") ||
    value.includes("credit") ||
    value.includes("debit") ||
    value.includes("visa") ||
    value.includes("master")
  ) {
    return "card";
  }

  if (
    value.includes("mobile") ||
    value.includes("momo") ||
    value.includes("mtn") ||
    value.includes("airtel") ||
    value.includes("orange")
  ) {
    return "mobile";
  }

  return value;
};

const getPaymentMethodValue = (method) => {
  if (!method) {
    return null;
  }

  if (typeof method !== "object") {
    return normalizePaymentMethod(method);
  }

  if (method.id !== undefined && method.id !== null) {
    return method.id;
  }

  return normalizePaymentMethod(method.slug || method.name);
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

const normalizeCategory = (category) => {
  return {
    ...category,
    id: category?.id,
    name: category?.name || "Unnamed category",
  };
};

const normalizeProduct = (product) => {
  const categoryId =
    product?.category?.id ?? product?.category_id ?? product?.category ?? null;

  const displayPrice = Number(product?.price ?? product?.base_price ?? 0);

  return {
    ...product,
    category_id: categoryId,
    display_price: Number.isFinite(displayPrice) ? displayPrice : 0,
  };
};




export default function POS() {
  const toast = useMemo(
    () => ({
      success: (message) => {
        window.alert(`SUCCESS: ${message}`);
      },

      error: (message) => {
        window.alert(`ERROR: ${message}`);
      },
    }),
    []
  );

  // ============================================================
  // VIEW AND SELECTION STATE
  // ============================================================

  const [view, setView] = useState("mode-select");

  const [selectedTable, setSelectedTable] = useState(null);

  const [activeOrder, setActiveOrder] = useState(null);

  const [activeProduct, setActiveProduct] = useState(null);

  const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);

  const [paymentMethods, setPaymentMethods] = useState([]);

  // ============================================================
  // UI STATE
  // ============================================================

  const [isModalOpen, setIsModalOpen] = useState(false);

  const [showPrintModal, setShowPrintModal] = useState(false);

  const [loading, setLoading] = useState(true);

  const [isSubmitting, setIsSubmitting] = useState(false);

  // ============================================================
  // DATA STATE
  // ============================================================

  const [tables, setTables] = useState([]);

  const [categories, setCategories] = useState([]);

  const [products, setProducts] = useState([]);

  const [selectedCategory, setSelectedCategory] = useState(null);

  const [currentSession, setCurrentSession] = useState(null);

  // ============================================================
  // PRINTING STATE
  // ============================================================

  const [printData, setPrintData] = useState(null);

  const [printType, setPrintType] = useState("receipt");

  // ============================================================
  // INITIAL DATA
  // ============================================================

  const fetchInitialData = useCallback(
    async (signal) => {
      setLoading(true);

      try {
        const [
          tableResponse,
          categoryResponse,
          productResponse,
          sessionResponse,
        ] = await Promise.all([
          api.get("/tables/", {
            signal,
            params: {
              _: Date.now(),
            },
          }),

          api.get("/manager/categories/", {
            signal,
            params: {
              _: Date.now(),
            },
          }),

          api.get("/manager/products/", {
            signal,
            params: {
              _: Date.now(),
            },
          }),

          api.get("/sessions/active/", {
            signal,
            params: {
              _: Date.now(),
            },
          }),
        ]);

        const tableData = getResponseList(tableResponse).map(normalizeTable);
        const categoryData =
          getResponseList(categoryResponse).map(normalizeCategory);

        const productData =
          getResponseList(productResponse).map(normalizeProduct);

        setTables(tableData);
        setCategories(categoryData);
        setProducts(productData);
        setCurrentSession(sessionResponse?.data || null);
      } catch (error) {
        if (isCanceledRequest(error)) {
          return;
        }

        console.error("Failed to fetch POS data:", error);

        toast.error(getErrorMessage(error, "Failed to load POS data."));
      } finally {
        if (!signal || !signal.aborted) {
          setLoading(false);
        }
      }
    },
    [toast]
  );

  const fetchPaymentMethods = useCallback(
    async (signal) => {
      try {
        const response = await api.get("/payment-methods/", {
          signal,
          params: {
            _: Date.now(),
          },
        });

        const methods = getResponseList(response);

        const activeMethods = methods.filter(
          (method) => method?.is_active !== false && method?.active !== false
        );

        setPaymentMethods(activeMethods);
      } catch (error) {
        if (isCanceledRequest(error)) {
          return;
        }

        console.error("Failed to fetch payment methods:", error);

        toast.error(getErrorMessage(error, "Could not load payment methods."));
      }
    },
    [toast]
  );

  useEffect(() => {
    const controller = new AbortController();

    fetchInitialData(controller.signal);

    fetchPaymentMethods(controller.signal);

    return () => {
      controller.abort();
    };
  }, [fetchInitialData, fetchPaymentMethods]);

  useEffect(() => {
    if (selectedCategory === null && categories.length > 0) {
      setSelectedCategory(categories[0].id);
    }
  }, [categories, selectedCategory]);

  // ============================================================
  // ORDER HELPERS
  // ============================================================

  const fetchFullOrder = useCallback(async (orderId) => {
    const response = await api.get(`/orders/${orderId}/`, {
      params: {
        _: Date.now(),
      },
    });

    return response.data;
  }, []);

  const refreshInitialData = async () => {
    await fetchInitialData();
  };

  // ============================================================
  // DINE-IN TABLE SELECTION
  // ============================================================

  const handleTableSelect = async (table) => {
    if (!table?.id) {
      toast.error("This table has no valid ID.");
      return;
    }

    const normalizedTable = normalizeTable(table);

    if (normalizedTable.is_available === false) {
      toast.error(`Table ${normalizedTable.display_number} is not available.`);
      return;
    }

    if (
      ["NEEDS_CLEANING", "MERGED", "INACTIVE"].includes(
        normalizedTable.current_status
      )
    ) {
      toast.error(
        `Table ${normalizedTable.display_number} cannot accept orders.`
      );
      return;
    }

    setLoading(true);

    try {
      setSelectedTable(normalizedTable);

      const response = await api.post("/orders/open_or_create/", {
        table: normalizedTable.id,
      });

      setActiveOrder(response.data);
      setView("menu");
    } catch (error) {
      console.error("Table select error:", error?.response?.data || error);

      toast.error(getErrorMessage(error, "Could not open table."));
    } finally {
      setLoading(false);
    }
  };

  // ============================================================
  // ADD ITEM TO ORDER
  // ============================================================

  const addToOrder = async (itemData) => {
    if (!activeOrder?.id) {
      toast.error("No active order found.");
      return;
    }

    if (!itemData?.product) {
      toast.error("No product selected.");
      return;
    }

    const quantity = Number(itemData.quantity);

    if (!Number.isInteger(quantity) || quantity <= 0 || quantity > 50) {
      toast.error("Quantity must be between 1 and 50.");
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = {
        order: activeOrder.id,
        product: itemData.product,
        quantity,
        modifiers: itemData.modifiers || [],
        notes: itemData.notes || "",
      };

      await api.post("/order-items/", payload);

      const updatedOrder = await fetchFullOrder(activeOrder.id);

      setActiveOrder(updatedOrder);
      setIsModalOpen(false);
      setActiveProduct(null);

      toast.success("Item added.");
    } catch (error) {
      console.error("Add item error:", error?.response?.data || error);

      toast.error(getErrorMessage(error, "Failed to add item."));
    } finally {
      setIsSubmitting(false);
    }
  };

  // ============================================================
  // SEND TO KITCHEN
  // ============================================================

  const handleSendToKitchen = async () => {
    if (
      !activeOrder?.id ||
      !Array.isArray(activeOrder.items) ||
      activeOrder.items.length === 0
    ) {
      toast.error("Cannot send an empty order to the kitchen.");
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await api.post(
        `/orders/${activeOrder.id}/send_to_kitchen/`
      );

      setActiveOrder(response.data);

      toast.success("Order sent to kitchen.");
    } catch (error) {
      console.error("Kitchen error:", error?.response?.data || error);

      toast.error(getErrorMessage(error, "Failed to send order to kitchen."));
    } finally {
      setIsSubmitting(false);
    }
  };

  // ============================================================
  // PAYMENT
  // ============================================================

  const handlePayment = () => {
    if (
      !activeOrder?.id ||
      !Array.isArray(activeOrder.items) ||
      activeOrder.items.length === 0
    ) {
      toast.error("Cannot pay for an empty order.");
      return;
    }

    const orderTotal = getOrderTotal(activeOrder);

    if (!Number.isFinite(orderTotal) || orderTotal <= 0) {
      toast.error("This order has a zero or invalid total.");
      return;
    }

    setIsPaymentModalOpen(true);
  };

  const handlePaymentComplete = async (orderId, methodId, paymentMethod) => {
    if (!orderId) {
      toast.error("Missing order ID.");
      return;
    }

    const orderTotal = getOrderTotal(activeOrder);

    if (!Number.isFinite(orderTotal) || orderTotal <= 0) {
      toast.error("This order has an invalid or zero total.");
      return;
    }

    let selectedMethod = methodId ?? paymentMethod;

    if (selectedMethod && typeof selectedMethod === "object") {
      selectedMethod = getPaymentMethodValue(selectedMethod);
    }

    if (!selectedMethod) {
      toast.error("Please select a payment method.");
      return;
    }

    setIsSubmitting(true);

    try {
      await api.post(`/orders/${orderId}/mark_paid/`, {
        payment_method: selectedMethod,
      });

      const updatedOrder = await fetchFullOrder(orderId);

      setActiveOrder(updatedOrder);
      setIsPaymentModalOpen(false);
      setSelectedTable(null);

      await refreshInitialData();

      toast.success("Payment successful.");

      setView("mode-select");
    } catch (error) {
      console.error("Payment failed:", error?.response?.data || error);

      toast.error(getErrorMessage(error, "Payment failed."));
    } finally {
      setIsSubmitting(false);
    }
  };

  // ============================================================
  // TAKE-OUT
  // ============================================================

  const handleTakeOutOrder = async (takeOutCart, customerInfo = {}) => {
    if (!Array.isArray(takeOutCart) || takeOutCart.length === 0) {
      toast.error("Cart is empty.");
      return;
    }

    if (!currentSession) {
      toast.error("Open the register before creating an order.");
      return;
    }

    setLoading(true);

    try {
      const customerName =
        customerInfo.customer_name?.trim() || "Walk-in Customer";

      const customerPhone = customerInfo.customer_phone?.trim();

      const notes = [
        `Customer: ${customerName}`,
        customerPhone ? `Phone: ${customerPhone}` : null,
      ]
        .filter(Boolean)
        .join("\n");

      const payload = {
        order_type: "TAKEOUT",
        notes,
        items: takeOutCart.map((item) => ({
          product: item.id,
          quantity: Number(item.quantity),
          modifiers:
            item.selectedModifiers?.map((modifier) => modifier.id) || [],
        })),
      };

      console.log("Take-out order payload:", payload);

      const response = await api.post("/orders/create_takeout/", payload);

      setActiveOrder(response.data);

      toast.success("Take-out order created.");

      setIsPaymentModalOpen(true);
    } catch (requestError) {
      console.error(
        "Take-out failed:",
        requestError?.response?.status,
        requestError?.response?.data || requestError
      );

      toast.error(getErrorMessage(requestError, "Take-out order failed."));

      throw requestError;
    } finally {
      setLoading(false);
    }
  };
  
  // ============================================================
  // RENDER: MODE SELECTION
  // ============================================================

  const renderModeSelection = () => {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6 text-center">
        <div className="max-w-4xl w-full">
          {!currentSession && (
            <div className="mb-8 p-4 bg-red-50 border border-red-200 text-red-700 rounded-2xl font-bold">
              No active session. Open the register in Settings.
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <button
              type="button"
              onClick={() => {
                setView("dine-in");
              }}
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
              type="button"
              onClick={() => {
                setView("take-out");
              }}
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
  };

  // ============================================================
  // RENDER: DINE-IN TABLES
  // ============================================================

  const renderDineIn = () => {
    return (
      <div className="p-6 bg-slate-50 min-h-screen">
        <div className="max-w-[1800px] mx-auto">
          <div className="flex items-center gap-4 mb-8">
            <button
              type="button"
              onClick={() => {
                setView("mode-select");
              }}
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
  };

  // ============================================================
  // RENDER: TAKE-OUT
  // ============================================================

  const renderTakeOut = () => {
    return (
      <div className="p-6 bg-slate-50 min-h-screen">
        <div className="max-w-[1800px] mx-auto">
          <div className="flex items-center gap-4 mb-8">
            <button
              type="button"
              onClick={() => {
                setView("mode-select");
              }}
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
  };

  // ============================================================
  // RENDER: MENU
  // ============================================================

  const renderMenu = () => {
    const displayedProducts = products.filter(
      (product) => !selectedCategory || product.category_id === selectedCategory
    );

    const orderItems = Array.isArray(activeOrder?.items)
      ? activeOrder.items
      : [];

    return (
      <div className="flex h-screen bg-slate-100 overflow-hidden">
        <div className="flex-1 flex flex-col overflow-hidden">
          <header className="bg-white border-b px-6 py-3 flex items-center justify-between shadow-sm">
            <div className="flex items-center gap-4">
              <button
                type="button"
                onClick={() => {
                  setView("dine-in");
                }}
                className="p-2 hover:bg-slate-100 rounded-xl">
                <ArrowLeft size={20} />
              </button>

              <div>
                <h2 className="text-lg font-black text-slate-900 leading-tight">
                  Table {selectedTable?.display_number}
                </h2>

                <span className="text-[9px] font-black uppercase tracking-widest text-indigo-600">
                  {activeOrder?.status || "DRAFT"}
                </span>
              </div>
            </div>

            <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide max-w-3xl">
              {categories.map((category) => (
                <button
                  type="button"
                  key={String(category.id)}
                  onClick={() => {
                    setSelectedCategory(category.id);
                  }}
                  className={`px-4 py-1.5 rounded-lg font-bold text-[11px] whitespace-nowrap transition-all ${
                    selectedCategory === category.id
                      ? "bg-indigo-600 text-white shadow-md"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}>
                  {category.name}
                </button>
              ))}
            </div>
          </header>

          <main className="flex-1 overflow-y-auto p-4 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-7 gap-3">
            {displayedProducts.map((product) => (
              <button
                type="button"
                key={String(product.id)}
                disabled={product.is_available === false}
                onClick={() => {
                  setActiveProduct(product);
                  setIsModalOpen(true);
                }}
                className="bg-white p-3 rounded-2xl shadow-sm border border-slate-100 hover:border-indigo-500 transition-all text-left flex flex-col justify-between min-h-[120px] disabled:opacity-50 disabled:cursor-not-allowed">
                <h3 className="font-bold text-slate-800 text-[13px] line-clamp-3">
                  {product.name}
                </h3>

                <div className="flex justify-between items-center mt-2 pt-2 border-t border-slate-50">
                  <span className="text-sm font-black text-indigo-600">
                    ${product.display_price.toFixed(2)}
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
              <ShoppingCart size={14} />
              Cart
            </h2>

            <span className="text-[9px] font-mono text-slate-400">
              #{String(activeOrder?.id || "").slice(0, 8)}
            </span>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {orderItems.length === 0 ? (
              <p className="text-sm text-slate-400 italic">
                No items added yet.
              </p>
            ) : (
              orderItems.map((item) => (
                <div
                  key={String(item.id)}
                  className="group border-b border-slate-50 pb-3">
                  <div className="flex justify-between items-start gap-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-[12px] font-bold text-slate-800 leading-tight">
                        {item.quantity}x{" "}
                        {item.product_name ||
                          item.product?.name ||
                          "Unnamed product"}
                      </p>

                      {item.modifiers?.length > 0 && (
                        <p className="text-[10px] text-slate-400 mt-1">
                          + {item.modifiers.length} modifiers
                        </p>
                      )}
                    </div>

                    <span className="text-[12px] font-black text-slate-900">
                      $
                      {Number(
                        item.total_price ??
                          Number(item.final_price || 0) *
                            Number(item.quantity || 0)
                      ).toFixed(2)}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="p-4 bg-slate-900 text-white">
            <div className="flex justify-between items-center mb-4">
              <span className="text-slate-400 text-[10px] font-bold uppercase tracking-widest">
                Total
              </span>

              <span className="text-2xl font-black">
                ${getOrderTotal(activeOrder).toFixed(2)}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={handleSendToKitchen}
                disabled={isSubmitting || orderItems.length === 0}
                className="bg-indigo-600 hover:bg-indigo-700 text-white py-4 rounded-xl font-black text-[11px] uppercase tracking-widest transition-colors disabled:opacity-50">
                Kitchen
              </button>

              <button
                type="button"
                onClick={handlePayment}
                disabled={
                  isSubmitting ||
                  orderItems.length === 0 ||
                  getOrderTotal(activeOrder) <= 0
                }
                className="bg-green-600 hover:bg-green-700 text-white py-4 rounded-xl font-black text-[11px] uppercase tracking-widest transition-colors disabled:opacity-50">
                Pay
              </button>
            </div>
          </div>
        </aside>
      </div>
    );
  };

  // ============================================================
  // RENDER CONTENT
  // ============================================================

  const renderContent = () => {
    if (view === "mode-select") {
      return renderModeSelection();
    }

    if (view === "dine-in") {
      return renderDineIn();
    }

    if (view === "take-out") {
      return renderTakeOut();
    }

    if (view === "menu") {
      return renderMenu();
    }

    return renderModeSelection();
  };

  if (loading && !tables.length && !products.length) {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-50">
        <Loader2
          className="animate-spin text-indigo-600"
          size={48}
        />
      </div>
    );
  }

  return (
    <>
      {renderContent()}

      <POSProductModal
        isOpen={isModalOpen}
        product={activeProduct}
        onClose={() => {
          setIsModalOpen(false);
          setActiveProduct(null);
        }}
        onAddToCart={addToOrder}
      />

      <PaymentModal
        isOpen={isPaymentModalOpen}
        order={activeOrder}
        methods={paymentMethods}
        onClose={() => {
          if (!isSubmitting) {
            setIsPaymentModalOpen(false);
          }
        }}
        onPaymentComplete={handlePaymentComplete}
      />

      {showPrintModal && (
        <div className="fixed inset-0 z-[999] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-[32px] p-8 max-w-sm w-full shadow-2xl text-center relative">
            <button
              type="button"
              onClick={() => {
                setShowPrintModal(false);
              }}
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
              type="button"
              onClick={() => {
                setShowPrintModal(false);
              }}
              className="w-full bg-slate-900 hover:bg-black text-white py-4 rounded-2xl font-black transition-all">
              CONTINUE
            </button>
          </div>
        </div>
      )}
    </>
  );
}
