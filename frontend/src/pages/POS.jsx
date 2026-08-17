import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Receipt,
  FileText,
  ChefHat,
  Wine,
  Armchair,
  ShoppingBag,
} from "lucide-react";
import api from "../services/api";
import PrintPreviewModal from "../components/printing/PrintPreviewModal";

export default function POS({ orderType = "dine-in" }) {
  const { tableId } = useParams();

  const isDineIn = orderType === "dine-in";
  const isTakeOut = orderType === "take-out";

  const [tables, setTables] = useState([]);
  const [activeTable, setActiveTable] = useState(null);

  const [order, setOrder] = useState(null);
  const [menu, setMenu] = useState([]);
  const [categories, setCategories] = useState([]);
  const [activeCategory, setActiveCategory] = useState(null);
  const [loadingOrder, setLoadingOrder] = useState(false);

  const [selectedProduct, setSelectedProduct] = useState(null);
  const [selectedOptions, setSelectedOptions] = useState({});

  const [printModalOpen, setPrintModalOpen] = useState(false);
  const [printOrder, setPrintOrder] = useState(null);
  const [printType, setPrintType] = useState("receipt");

  const formatMoney = (value) =>
    value !== undefined && value !== null && !Number.isNaN(Number(value))
      ? Number(value).toFixed(2)
      : "0.00";

  const getUnitPrice = (item) => {
    const quantity = Number(item.quantity || 1);

    const explicitUnitPrice =
      item.unit_price ??
      item.unitPrice ??
      item.product?.base_price ??
      item.product?.price ??
      item.product_base_price ??
      item.base_price;

    if (explicitUnitPrice !== undefined && explicitUnitPrice !== null) {
      return Number(explicitUnitPrice);
    }

    if (item.final_price !== undefined && item.final_price !== null) {
      return Number(item.final_price) / quantity;
    }

    return 0;
  };

  const getLineTotal = (item) => {
    const quantity = Number(item.quantity || 1);

    const explicitLineTotal =
      item.line_total ??
      item.lineTotal ??
      item.total_price ??
      item.totalPrice ??
      item.total ??
      item.final_price;

    if (explicitLineTotal !== undefined && explicitLineTotal !== null) {
      return Number(explicitLineTotal);
    }

    return getUnitPrice(item) * quantity;
  };

  const openPrintPreview = (orderToPrint, type) => {
    setPrintOrder(orderToPrint);
    setPrintType(type);
    setPrintModalOpen(true);
  };

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

  const addOrderItem = async (product, modifierIds = []) => {
    try {
      const payload = {
        order: order.id,
        product_id: product.id,
        quantity: 1,
        modifier_ids: modifierIds,
      };

      console.log("ADDING ITEM PAYLOAD:", payload);

      await api.post("/v1/order-items/", payload);
      await refreshOrder();
      setSelectedProduct(null);
    } catch (error) {
      console.log("FULL ERROR:", error);
      console.log("STATUS:", error.response?.status);
      console.log("DATA:", JSON.stringify(error.response?.data, null, 2));
      console.error("Failed to add order item:", error);
      console.error("POST ERROR DATA:", error.response?.data);
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
    if (!selectedProduct) return;

    const allSelected = Object.values(selectedOptions)
      .flat()
      .map((opt) => opt.id);

    addOrderItem(selectedProduct, allSelected);
  };

  /* ================= FETCH TABLES ================= */

  useEffect(() => {
    if (isDineIn) {
      fetchTables();
    }
  }, [isDineIn]);

  const fetchTables = async () => {
    try {
      const res = await api.get("/v1/tables/");
      setTables(res.data.results || res.data);
    } catch (err) {
      console.error(err);
    }
  };

  /* ================= ACTIVE TABLE FROM URL ================= */

  useEffect(() => {
    if (tableId && isDineIn) {
      setActiveTable(tableId);
    }
  }, [tableId, isDineIn]);

  /* ================= OPEN DINE-IN ORDER ================= */

  useEffect(() => {
    if (!isDineIn) return;
    if (!activeTable) return;

    const openOrder = async () => {
      try {
        setLoadingOrder(true);

        const res = await api.post("/v1/orders/open_or_create/", {
          table_id: activeTable,
        });

        setOrder(res.data);
      } catch (err) {
        console.error("Error opening dine-in order:", err);
        console.error("OPEN DINE-IN ORDER ERROR DATA:", err.response?.data);
      } finally {
        setLoadingOrder(false);
      }
    };

    openOrder();
  }, [activeTable, isDineIn]);

  /* ================= OPEN TAKE-OUT ORDER ================= */

  useEffect(() => {
    if (!isTakeOut) return;

    const openTakeOutOrder = async () => {
      try {
        setLoadingOrder(true);

        const res = await api.post("/v1/orders/open_or_create/", {
          order_type: "TAKE_OUT",
        });

        setOrder(res.data);
      } catch (err) {
        console.error("Error opening take-out order:", err);
        console.error("OPEN TAKE-OUT ORDER ERROR DATA:", err.response?.data);
      } finally {
        setLoadingOrder(false);
      }
    };

    openTakeOutOrder();
  }, [isTakeOut]);

  /* ================= LOAD MENU + CATEGORIES ================= */

  useEffect(() => {
    const fetchMenuData = async () => {
      try {
        const [productsRes, categoriesRes] = await Promise.all([
          api.get("/v1/products/"),
          api.get("/v1/categories/"),
        ]);

        setMenu(productsRes.data.results || productsRes.data);
        setCategories(categoriesRes.data.results || categoriesRes.data);
      } catch (err) {
        console.error("Error loading menu data:", err);
        console.error("MENU DATA ERROR:", err.response?.data);
      }
    };

    fetchMenuData();
  }, []);

  /* ================= ORDER ACTIONS ================= */

  const refreshOrder = async () => {
    if (!order?.id) return;

    try {
      const res = await api.get(`/v1/orders/${order.id}/`);
      setOrder(res.data);
    } catch (err) {
      console.error("Failed to refresh order:", err);
      console.error("REFRESH ORDER ERROR DATA:", err.response?.data);
    }
  };

  const increaseQty = async (item) => {
    try {
      await api.patch(`/v1/order-items/${item.id}/`, {
        quantity: Number(item.quantity || 1) + 1,
      });

      await refreshOrder();
    } catch (err) {
      console.error("Failed to increase quantity:", err);
      console.error("PATCH ERROR DATA:", err.response?.data);
    }
  };

  const decreaseQty = async (item) => {
    const currentQuantity = Number(item.quantity || 1);

    if (currentQuantity <= 1) return;

    try {
      await api.patch(`/v1/order-items/${item.id}/`, {
        quantity: currentQuantity - 1,
      });

      await refreshOrder();
    } catch (err) {
      console.error("Failed to decrease quantity:", err);
      console.error("PATCH ERROR DATA:", err.response?.data);
    }
  };

  const removeItem = async (item) => {
    try {
      await api.delete(`/v1/order-items/${item.id}/`);
      await refreshOrder();
    } catch (err) {
      console.error("Failed to remove item:", err);
      console.error("REMOVE ITEM ERROR DATA:", err.response?.data);
    }
  };

  const sendToKitchen = async () => {
    if (!order?.id) return;

    try {
      await api.post(`/v1/orders/${order.id}/send_to_kitchen/`);
      await refreshOrder();
    } catch (err) {
      console.error("Failed to send order to kitchen:", err);
      console.error("SEND TO KITCHEN ERROR DATA:", err.response?.data);
    }
  };

  const markPaid = async () => {
    if (!order?.id) return;

    try {
      await api.post(`/v1/orders/${order.id}/mark_paid/`);
      setOrder(null);
      setActiveTable(null);

      if (isDineIn) {
        fetchTables();
      }

      if (isTakeOut) {
        const res = await api.post("/v1/orders/open_or_create/", {
          order_type: "TAKE_OUT",
        });

        setOrder(res.data);
      }
    } catch (err) {
      console.error("Mark paid failed:", err);
      console.error("MARK PAID ERROR DATA:", err.response?.data);
    }
  };

  const changeTable = () => {
    setActiveTable(null);
    setOrder(null);
    setSelectedProduct(null);
    setSelectedOptions({});
  };

  /* ================= UI STATE ================= */

  const orderItems = order?.items || order?.order_items || [];

  const normalizedOrderStatus = String(order?.status || "DRAFT").toUpperCase();

  const normalizedPaymentStatus = String(
    order?.payment_status || order?.paymentStatus || "UNPAID"
  ).toUpperCase();

  const hasItems = orderItems.length > 0;

  const canSendToKitchen =
    Boolean(order?.id) && hasItems && normalizedOrderStatus === "DRAFT";

  const canMarkPaid =
    Boolean(order?.id) && hasItems && normalizedPaymentStatus !== "PAID";

  const calculatedTotal =
    orderItems.reduce((sum, item) => {
      return sum + getLineTotal(item);
    }, 0) || 0;

  const displayTotal = calculatedTotal;

  const selectedTable = tables.find(
    (table) => String(table.id) === String(activeTable)
  );
  
  const getCategoryIdFromProduct = (product) => {
    // Nested object
    if (product.category?.id != null) {
      return String(product.category.id);
    }

    // Flat category_id field
    if (product.category_id != null) {
      return String(product.category_id);
    }

    // Plain category field (number or string)
    if (product.category != null) {
      return String(product.category);
    }

    return null;
  };

  const productsForActiveCategory = activeCategory
    ? menu.filter(
        (product) =>
          getCategoryIdFromProduct(product) === String(activeCategory.id)
      )
    : [];

  const renderMenuPanel = () => {
    if (!activeCategory) {
      return (
        <>
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold">Categories</h2>

              <p className="text-sm text-gray-500">
                Select a category to view menu items.
              </p>
            </div>

            {isDineIn && selectedTable && (
              <button
                type="button"
                onClick={changeTable}
                className="rounded bg-gray-200 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-300">
                Change Table
              </button>
            )}
          </div>

          {categories.length === 0 && (
            <div className="rounded-lg border border-dashed border-gray-300 p-6 text-center text-sm text-gray-500">
              No categories found.
            </div>
          )}

          <div className="grid grid-cols-3 gap-4">
            {categories.map((category) => (
              <button
                key={category.id}
                type="button"
                onClick={() => setActiveCategory(category)}
                className="min-h-32 rounded-xl bg-blue-50 p-5 text-left shadow-sm transition hover:bg-blue-100">
                <div className="text-xl font-bold text-blue-900">
                  {category.name}
                </div>

                {category.description && (
                  <div className="mt-2 text-sm text-blue-700">
                    {category.description}
                  </div>
                )}
              </button>
            ))}
          </div>
        </>
      );
    }

    return (
      <>
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold">{activeCategory.name}</h2>

            <p className="text-sm text-gray-500">
              Select an item to add to the order.
            </p>
          </div>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setActiveCategory(null)}
              className="rounded bg-gray-200 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-300">
              Back to Categories
            </button>

            {isDineIn && selectedTable && (
              <button
                type="button"
                onClick={changeTable}
                className="rounded bg-gray-200 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-300">
                Change Table
              </button>
            )}
          </div>
        </div>

        {loadingOrder && (
          <div className="mb-4 rounded bg-blue-50 px-3 py-2 text-sm text-blue-700">
            Loading order...
          </div>
        )}

        {productsForActiveCategory.length === 0 && (
          <div className="rounded-lg border border-dashed border-gray-300 p-6 text-center text-sm text-gray-500">
            No items found in this category.
          </div>
        )}

        <div className="grid grid-cols-3 gap-4">
          {productsForActiveCategory.map((product) => (
            <button
              key={product.id}
              type="button"
              onClick={() => handleAddProduct(product)}
              disabled={!order}
              className={`min-h-32 rounded-xl p-5 text-left shadow-sm transition ${
                order
                  ? "bg-gray-100 hover:bg-gray-200"
                  : "cursor-not-allowed bg-gray-50 text-gray-400"
              }`}>
              <div className="text-lg font-bold text-gray-800">
                {product.name}
              </div>

              {product.description && (
                <div className="mt-2 line-clamp-2 text-sm text-gray-500">
                  {product.description}
                </div>
              )}

              <div className="mt-3 text-base font-semibold text-gray-600">
                ${formatMoney(product.base_price ?? product.price)}
              </div>

              {product.modifier_groups?.length > 0 && (
                <div className="mt-3 inline-flex rounded-full bg-purple-100 px-3 py-1 text-xs font-bold text-purple-700">
                  Options
                </div>
              )}
            </button>
          ))}
        </div>
      </>
    );
  };

  const renderOrderPanel = () => {
    if (!order) {
      return (
        <div className="rounded-lg border border-dashed border-gray-300 p-6 text-center text-sm text-gray-500">
          {isDineIn ? "Opening table order..." : "Preparing take-out order..."}
        </div>
      );
    }

    return (
      <>
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold">
              Order #{order.display_id || order.id}
            </h2>

            <div className="mt-1 text-sm text-gray-500">
              {isDineIn && selectedTable && (
                <>Table {selectedTable.table_number} • </>
              )}
              {isTakeOut && <>Take-out • </>}
              Status: {normalizedOrderStatus}{" "}
              {normalizedPaymentStatus && (
                <>• Payment: {normalizedPaymentStatus}</>
              )}
            </div>
          </div>
        </div>

        {orderItems.length === 0 && (
          <div className="mb-4 rounded-lg border border-dashed border-gray-300 p-6 text-center text-sm text-gray-400">
            No items added yet.
          </div>
        )}

        {orderItems.map((item) => (
          <div
            key={item.id}
            className="mb-3 rounded bg-gray-100 p-3">
            <div className="flex justify-between gap-3">
              <div>{item.product?.name || item.product_name || "Item"}</div>

              <button
                type="button"
                onClick={() => removeItem(item)}
                className="text-gray-500 hover:text-red-600">
                ✕
              </button>
            </div>

            {item.modifiers?.map((opt) => (
              <div
                key={opt.id}
                className="text-sm text-gray-600">
                + {opt.name}
              </div>
            ))}

            <div className="mt-2 flex justify-between">
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => decreaseQty(item)}
                  className="rounded bg-white px-2">
                  -
                </button>

                <span>{item.quantity}</span>

                <button
                  type="button"
                  onClick={() => increaseQty(item)}
                  className="rounded bg-white px-2">
                  +
                </button>
              </div>

              <div className="text-right">
                <div>${formatMoney(getLineTotal(item))}</div>

                <div className="text-xs text-gray-500">
                  ${formatMoney(getUnitPrice(item))} each
                </div>
              </div>
            </div>
          </div>
        ))}

        <div className="flex justify-between border-t pt-4 text-lg font-bold">
          <span>Total</span>
          <span>${formatMoney(displayTotal)}</span>
        </div>

        {/* PRINT BUTTONS */}
        <div className="mt-6 grid grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() => openPrintPreview(order, "bill")}
            disabled={!hasItems}
            className={`inline-flex items-center justify-center gap-2 rounded py-2 text-sm font-semibold ${
              hasItems
                ? "border border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
                : "cursor-not-allowed bg-gray-200 text-gray-400"
            }`}>
            <FileText size={16} />
            Bill
          </button>

          <button
            type="button"
            onClick={() => openPrintPreview(order, "receipt")}
            disabled={!hasItems}
            className={`inline-flex items-center justify-center gap-2 rounded py-2 text-sm font-semibold ${
              hasItems
                ? "border border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
                : "cursor-not-allowed bg-gray-200 text-gray-400"
            }`}>
            <Receipt size={16} />
            Receipt
          </button>

          <button
            type="button"
            onClick={() => openPrintPreview(order, "kitchen")}
            disabled={!hasItems}
            className={`inline-flex items-center justify-center gap-2 rounded py-2 text-sm font-semibold ${
              hasItems
                ? "border border-orange-300 bg-orange-50 text-orange-700 hover:bg-orange-100"
                : "cursor-not-allowed bg-gray-200 text-gray-400"
            }`}>
            <ChefHat size={16} />
            Kitchen Ticket
          </button>

          <button
            type="button"
            onClick={() => openPrintPreview(order, "bar")}
            disabled={!hasItems}
            className={`inline-flex items-center justify-center gap-2 rounded py-2 text-sm font-semibold ${
              hasItems
                ? "border border-purple-300 bg-purple-50 text-purple-700 hover:bg-purple-100"
                : "cursor-not-allowed bg-gray-200 text-gray-400"
            }`}>
            <Wine size={16} />
            Bar Ticket
          </button>
        </div>

        {/* ORDER ACTION BUTTONS */}
        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={sendToKitchen}
            disabled={!canSendToKitchen}
            className={`flex-1 rounded py-2 text-white ${
              canSendToKitchen
                ? "bg-orange-600 hover:bg-orange-700"
                : "cursor-not-allowed bg-gray-400"
            }`}>
            {normalizedOrderStatus === "DRAFT"
              ? "Send to Kitchen"
              : "Sent to Kitchen"}
          </button>

          <button
            type="button"
            onClick={markPaid}
            disabled={!canMarkPaid}
            className={`flex-1 rounded py-2 text-white ${
              canMarkPaid
                ? "bg-green-600 hover:bg-green-700"
                : "cursor-not-allowed bg-gray-400"
            }`}>
            {normalizedPaymentStatus === "PAID" ? "Paid" : "Mark Paid"}
          </button>
        </div>
      </>
    );
  };

  return (
    <div className="h-screen overflow-hidden">
      {/* PAGE HEADER */}
      <div className="mb-4 flex items-center justify-between border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">
            {isDineIn ? "Dine-in" : "Take-out"}
          </h1>

          <p className="text-sm text-gray-500">
            {isDineIn
              ? "Select a table first, then add menu items to the order."
              : "Add menu items directly to a take-out order."}
          </p>
        </div>

        <div className="flex items-center gap-2 rounded-full bg-gray-100 px-4 py-2 text-sm font-semibold text-gray-700">
          {isDineIn ? <Armchair size={16} /> : <ShoppingBag size={16} />}
          {isDineIn
            ? selectedTable
              ? `Table ${selectedTable.table_number}`
              : "No table selected"
            : "Take-out"}
        </div>
      </div>

      <div className="h-[calc(100vh-130px)]">

        {/* DINE-IN: BEFORE TABLE SELECTED — FULL FLOOR PLAN */}
        {isDineIn && !activeTable && (
          <div className="h-full overflow-y-auto rounded-xl bg-slate-100 p-6">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-gray-800">
                  Restaurant Floor Plan
                </h2>
                <p className="text-sm text-gray-500">
                  Select a table to start or continue an order.
                </p>
              </div>

              <div className="rounded-full bg-white px-4 py-2 text-sm font-semibold text-gray-600 shadow">
                {tables.length} Tables
              </div>
            </div>

            {/* ROOM / FLOOR PLAN */}
            <div className="relative min-h-[620px] rounded-3xl border-4 border-slate-300 bg-white p-8 shadow-inner">
              {/* DECORATIVE ROOM LABELS */}
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

              {/* TABLE ARRANGEMENT */}
              <div className="grid h-full min-h-[560px] grid-cols-4 gap-8 pt-16">
                {tables.map((table) => {
                  const status = String(
                    table.status || "AVAILABLE"
                  ).toUpperCase();

                  const isOccupied =
                    status === "OCCUPIED" ||
                    status === "OPEN" ||
                    status === "IN_USE";

                  const isReserved = status === "RESERVED";

                  const tableShape =
                    Number(table.seats || 0) >= 6
                      ? "rounded-2xl"
                      : "rounded-full";

                  return (
                    <button
                      key={table.id}
                      type="button"
                      onClick={() => setActiveTable(table.id)}
                      className={`relative flex min-h-36 flex-col items-center justify-center border-4 p-5 text-center shadow-lg transition hover:scale-105 ${tableShape} ${
                        isOccupied
                          ? "border-red-300 bg-red-100 text-red-800"
                          : isReserved
                          ? "border-yellow-300 bg-yellow-100 text-yellow-800"
                          : "border-green-300 bg-green-100 text-green-800"
                      }`}>
                      {/* CHAIRS */}
                      <div className="absolute -top-4 left-1/2 h-7 w-12 -translate-x-1/2 rounded-full bg-slate-300" />
                      <div className="absolute -bottom-4 left-1/2 h-7 w-12 -translate-x-1/2 rounded-full bg-slate-300" />
                      <div className="absolute -left-4 top-1/2 h-12 w-7 -translate-y-1/2 rounded-full bg-slate-300" />
                      <div className="absolute -right-4 top-1/2 h-12 w-7 -translate-y-1/2 rounded-full bg-slate-300" />

                      <div className="text-xl font-black">
                        Table {table.table_number}
                      </div>

                      <div className="mt-1 text-sm font-semibold opacity-80">
                        {table.seats || 4} seats
                      </div>

                      <div className="mt-3 rounded-full bg-white/70 px-3 py-1 text-xs font-bold">
                        {isOccupied
                          ? "Occupied"
                          : isReserved
                          ? "Reserved"
                          : "Available"}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* DINE-IN: AFTER TABLE SELECTED */}
        {isDineIn && activeTable && (
          <div className="grid h-full grid-cols-5">
            {/* MENU */}
            <div className="col-span-3 overflow-y-auto border-r p-5">
              {renderMenuPanel()}
            </div>

            {/* ORDER */}
            <div className="col-span-2 overflow-y-auto p-6">
              {renderOrderPanel()}
            </div>
          </div>
        )}

        {/* TAKE-OUT: MENU + ORDER ONLY */}
{isTakeOut && (
  <div className="grid h-full grid-cols-5">
    {/* MENU */}
    <div className="col-span-3 overflow-y-auto border-r p-5">
      {renderMenuPanel()}
    </div>

    {/* ORDER */}
    <div className="col-span-2 overflow-y-auto p-6">
      {renderOrderPanel()}
    </div>
  </div>
)}
</div>

      {/* MODIFIER MODAL */}
      {selectedProduct && (
        <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-40">
          <div className="w-96 rounded bg-white p-6">
            <h3 className="mb-4 text-lg font-semibold">
              {selectedProduct.name}
            </h3>

            {selectedProduct.modifier_groups.map((group) => (
              <div
                key={group.id}
                className="mb-4">
                <div className="font-medium">{group.name}</div>

                {group.options.map((option) => {
                  const selectedForGroup = selectedOptions[group.id] || [];
                  const checked = selectedForGroup.some(
                    (selected) => selected.id === option.id
                  );

                  return (
                    <label
                      key={option.id}
                      className="block text-sm">
                      <input
                        type={
                          group.selection_type === "SINGLE"
                            ? "radio"
                            : "checkbox"
                        }
                        name={String(group.id)}
                        checked={checked}
                        onChange={() => handleOptionSelect(group, option)}
                        className="mr-2"
                      />
                      {option.name} (+{formatMoney(option.price_adjustment)})
                    </label>
                  );
                })}
              </div>
            ))}

            <div className="mt-4 flex gap-2">
              <button
                type="button"
                onClick={confirmModifiers}
                className="flex-1 rounded bg-blue-600 py-2 text-white">
                Add
              </button>

              <button
                type="button"
                onClick={() => setSelectedProduct(null)}
                className="flex-1 rounded bg-gray-300 py-2">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <PrintPreviewModal
        open={printModalOpen}
        onClose={() => setPrintModalOpen(false)}
        order={printOrder}
        type={printType}
      />
    </div>
  );
}