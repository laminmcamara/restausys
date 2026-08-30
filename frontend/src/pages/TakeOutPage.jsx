import React, { useMemo, useState } from "react";

export default function TakeOutPage({
  // Pass these from parent (so nothing is hardcoded)
  restaurantName,
  orderLabel = "T/o", // configurable; parent can pass "T/o" / "T/O" / etc.
  menus = [], // [{ id, name, price }]
  onSendOrder, // async fn(payload) => promise
  paymentMethods = ["Cash", "Card"], // optional if you want to support receipts later
}) {
  const [cart, setCart] = useState([]);
  const [tableRef, setTableRef] = useState(""); // optional if your take-out needs a custom label

  const cartTotal = useMemo(() => {
    return cart.reduce((total, item) => total + item.price * item.quantity, 0);
  }, [cart]);

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

  const orderIdentifier = tableRef?.trim() ? tableRef.trim() : orderLabel;

  const sendDisabled = cart.length === 0 || typeof onSendOrder !== "function";

  const handleSend = async () => {
    if (sendDisabled) return;

    const payload = {
      orderType: "TAKE_OUT",
      identifier: orderIdentifier, // e.g. "T/o"
      restaurantName,
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
      // Kitchen/Customer/Receipt printing should be driven by backend,
      // but we include info needed for the 3 templates:
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
    setTableRef("");
  };

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <section className="rounded-3xl bg-white p-6 shadow-sm lg:col-span-2">
        <h1 className="text-3xl font-black text-slate-900">Take-out</h1>
        <p className="mt-1 text-sm text-slate-500">
          Add menu items to your take-out order.
        </p>

        {/* Optional: allow user to override identifier (still not hardcoded) */}
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div className="sm:col-span-2">
            <label className="block text-sm font-black text-slate-900">
              Order label
            </label>
            <input
              value={tableRef}
              onChange={(e) => setTableRef(e.target.value)}
              placeholder={`Default: ${orderLabel}`}
              className="mt-2 w-full rounded-xl border border-slate-200 bg-white p-3 text-sm outline-none focus:ring-2 focus:ring-blue-600/30"
            />
          </div>
        </div>

        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
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
      </section>

      <aside className="rounded-3xl bg-white p-6 shadow-sm">
        <h2 className="text-xl font-black text-slate-900">Take-out Cart</h2>

        <div className="mt-6 space-y-3">
          {cart.length === 0 ? (
            <p className="text-sm text-slate-500">Cart is empty.</p>
          ) : (
            cart.map((item) => (
              <div
                key={item.id}
                className="rounded-xl border border-slate-100 p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-bold text-slate-800">{item.name}</p>
                    <p className="text-sm text-slate-500">
                      ${Number(item.price).toFixed(2)} × {item.quantity}
                    </p>
                    <p className="mt-1 font-black text-slate-900">
                      ${(item.price * item.quantity).toFixed(2)}
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={() => removeFromCart(item.id)}
                    className="rounded-lg px-2 py-1 text-xs font-black text-slate-600 hover:bg-slate-50"
                    aria-label={`Remove ${item.name}`}>
                    ✕
                  </button>
                </div>

                <div className="mt-3 flex items-center justify-between">
                  <button
                    type="button"
                    onClick={() => setQty(item.id, item.quantity - 1)}
                    className="rounded-lg border border-slate-200 px-3 py-1 text-xs font-black text-slate-700 hover:bg-slate-50">
                    -
                  </button>

                  <span className="text-sm font-black text-slate-900">
                    {item.quantity}
                  </span>

                  <button
                    type="button"
                    onClick={() => setQty(item.id, item.quantity + 1)}
                    className="rounded-lg border border-slate-200 px-3 py-1 text-xs font-black text-slate-700 hover:bg-slate-50">
                    +
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
            disabled={cart.length === 0}
            onClick={handleSend}
            className="mt-5 w-full rounded-xl bg-blue-600 px-4 py-3 font-black text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300">
            Send Order
          </button>
        </div>

        {/* Optional: show the identifier that will be printed on kitchen/customer/receipt */}
        <div className="mt-4 text-xs text-slate-500">
          Order label:{" "}
          <span className="font-black text-slate-800">{orderIdentifier}</span>
        </div>
      </aside>
    </div>
  );
}
