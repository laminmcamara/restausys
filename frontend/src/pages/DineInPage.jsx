import React, { useMemo, useState } from "react";

export default function DineInPage({
  restaurantName,
  floorTables = [], // [{ id, name, seats, status }]
  menus = [], // [{ id, name, price }]
  onSendOrder, // async fn(payload) => promise
  tableIdentifierPrefix = "", // optional, e.g. "" => use table.name, or "T" => T1 style
}) {
  const [selectedTableId, setSelectedTableId] = useState(null);
  const [cart, setCart] = useState([]);

  const selectedTable = useMemo(() => {
    return floorTables.find((t) => t.id === selectedTableId) || null;
  }, [floorTables, selectedTableId]);

  const visibleTables = selectedTable ? [selectedTable] : floorTables;

  const addToCart = (item) => {
    setCart((prev) => {
      const existing = prev.find((ci) => ci.id === item.id);
      if (existing) {
        return prev.map((ci) =>
          ci.id === item.id ? { ...ci, quantity: ci.quantity + 1 } : ci
        );
      }
      return [...prev, { ...item, quantity: 1 }];
    });
  };

  const removeFromCart = (id) => {
    setCart((prev) => prev.filter((x) => x.id !== id));
  };

  const setQty = (id, qty) => {
    setCart((prev) =>
      prev
        .map((x) => (x.id === id ? { ...x, quantity: qty } : x))
        .filter((x) => x.quantity > 0)
    );
  };

  const cartTotal = useMemo(() => {
    return cart.reduce((total, item) => total + item.price * item.quantity, 0);
  }, [cart]);

  const getTableLabel = (table) => {
    if (!table) return "";
    // If caller wants prefix-based labels, they can pass tableIdentifierPrefix="T"
    // and also ensure table.name is something like "1" or they handle it upstream.
    // Default: use table.name directly.
    if (!tableIdentifierPrefix) return table.name;
    const suffix = String(table.name).replace(/^T\s*/i, "").trim();
    return `${tableIdentifierPrefix}${suffix}`;
  };

  const identifier = selectedTable ? getTableLabel(selectedTable) : "";

  const sendDisabled =
    !selectedTable || cart.length === 0 || typeof onSendOrder !== "function";

  const handleSend = async () => {
    if (sendDisabled) return;

    const payload = {
      orderType: "DINE_IN",
      identifier, // e.g. T1
      restaurantName,
      tableId: selectedTable.id,

      items: cart.map((i) => ({
        menuId: i.id,
        name: i.name,
        price: i.price,
        quantity: i.quantity,
        lineTotal: i.price * i.quantity,
      })),

      totals: {
        subtotal: cartTotal,
        total: cartTotal,
      },

      // Drives your 3 printouts on backend:
      ticketMeta: {
        kitchen: {
          showAmounts: false,
          showRestaurantName: false,
          showPayment: false,
          identifier,
        },
        customerTicket: {
          showAmounts: true,
          showRestaurantName: true,
          showPayment: false,
          identifier,
        },
        receipt: {
          showAmounts: true,
          showRestaurantName: true,
          showPayment: true,
          identifier,
        },
      },
    };

    await onSendOrder(payload);
    setCart([]);
    setSelectedTableId(null);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-black text-slate-900">Dine-in</h1>
        <p className="mt-1 text-sm text-slate-500">
          Select a table first, then add menu items to the cart.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <section className="rounded-3xl bg-white p-6 shadow-sm lg:col-span-2">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <h2 className="text-xl font-black text-slate-900">
                Salon / Floorplan
              </h2>
              <p className="text-sm text-slate-500">
                Choose an available table.
              </p>
            </div>

            {selectedTable && (
              <button
                type="button"
                onClick={() => {
                  setSelectedTableId(null);
                  setCart([]);
                }}
                className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-100">
                Change Table
              </button>
            )}
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {visibleTables.map((table) => {
              const isOccupied = table.status === "occupied";
              const isSelected = selectedTable?.id === table.id;

              return (
                <button
                  key={table.id}
                  type="button"
                  disabled={isOccupied && !isSelected}
                  onClick={() => {
                    if (!isOccupied) setSelectedTableId(table.id);
                  }}
                  className={`rounded-3xl border p-6 text-left transition ${
                    isSelected
                      ? "border-blue-600 bg-blue-50 ring-4 ring-blue-100"
                      : isOccupied
                      ? "cursor-not-allowed border-red-200 bg-red-50 opacity-60"
                      : "border-slate-200 bg-slate-50 hover:border-blue-500 hover:bg-blue-50"
                  }`}>
                  <div className="flex items-center justify-between">
                    <span className="text-lg font-black text-slate-900">
                      {table.name}
                    </span>
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-black ${
                        isSelected
                          ? "bg-blue-600 text-white"
                          : isOccupied
                          ? "bg-red-600 text-white"
                          : "bg-green-600 text-white"
                      }`}>
                      {isSelected
                        ? "Selected"
                        : isOccupied
                        ? "Occupied"
                        : "Available"}
                    </span>
                  </div>

                  <p className="mt-4 text-sm font-bold text-slate-500">
                    Seats: {table.seats}
                  </p>
                </button>
              );
            })}
          </div>
        </section>

        <aside className="rounded-3xl bg-white p-6 shadow-sm">
          <h2 className="text-xl font-black text-slate-900">Cart</h2>

          {selectedTable ? (
            <p className="mt-1 text-sm font-bold text-blue-600">
              {selectedTable.name}
            </p>
          ) : (
            <p className="mt-1 text-sm text-slate-500">
              No table selected yet.
            </p>
          )}

          <div className="mt-6 space-y-3">
            {cart.length === 0 ? (
              <p className="text-sm text-slate-500">Cart is empty.</p>
            ) : (
              cart.map((item) => (
                <div
                  key={item.id}
                  className="flex items-start justify-between gap-3 border-b border-slate-100 pb-3">
                  <div>
                    <p className="font-bold text-slate-800">{item.name}</p>
                    <p className="text-sm text-slate-500">
                      ${Number(item.price).toFixed(2)} × {item.quantity}
                    </p>
                  </div>

                  <div className="flex flex-col items-end gap-2">
                    <p className="font-black text-slate-900">
                      ${(item.price * item.quantity).toFixed(2)}
                    </p>
                    <button
                      type="button"
                      onClick={() => removeFromCart(item.id)}
                      className="rounded-lg px-2 py-1 text-xs font-black text-slate-600 hover:bg-slate-50"
                      aria-label={`Remove ${item.name}`}>
                      ✕
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="mt-6 border-t border-slate-200 pt-4">
            <div className="flex items-center justify-between">
              <span className="font-black text-slate-900">Total</span>
              <span className="text-xl font-black text-slate-900">
                ${cartTotal.toFixed(2)}
              </span>
            </div>

            <button
              type="button"
              disabled={!selectedTable || cart.length === 0}
              onClick={handleSend}
              className="mt-5 w-full rounded-xl bg-blue-600 px-4 py-3 font-black text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300">
              Send Order
            </button>
          </div>
        </aside>
      </div>

      {selectedTable && (
        <section className="rounded-3xl bg-white p-6 shadow-sm">
          <h2 className="text-xl font-black text-slate-900">Menus</h2>
          <p className="mt-1 text-sm text-slate-500">
            Add items for {selectedTable.name}.
          </p>

          <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {menus.map((item) => (
              <div
                key={item.id}
                className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                <h3 className="font-black text-slate-900">{item.name}</h3>
                <p className="mt-2 text-lg font-black text-blue-600">
                  ${Number(item.price).toFixed(2)}
                </p>

                <button
                  type="button"
                  onClick={() => addToCart(item)}
                  className="mt-4 w-full rounded-xl bg-slate-900 px-4 py-3 text-sm font-black text-white transition hover:bg-slate-700">
                  Add to Cart
                </button>
              </div>
            ))}
          </div>

          {/* optional: show identifier used on kitchen/customer/receipt */}
          <div className="mt-4 text-xs text-slate-500">
            Order label:{" "}
            <span className="font-black text-slate-800">{identifier}</span>
          </div>
        </section>
      )}
    </div>
  );
}
