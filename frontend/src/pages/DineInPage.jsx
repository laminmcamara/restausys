import React, { useState } from "react";

const tables = [
  { id: 1, name: "Table 1", seats: 2, status: "available" },
  { id: 2, name: "Table 2", seats: 4, status: "available" },
  { id: 3, name: "Table 3", seats: 4, status: "occupied" },
  { id: 4, name: "Table 4", seats: 6, status: "available" },
  { id: 5, name: "Table 5", seats: 2, status: "available" },
  { id: 6, name: "Table 6", seats: 8, status: "available" },
];

const menus = [
  { id: 1, name: "Chicken Burger", price: 8.99 },
  { id: 2, name: "Beef Burger", price: 9.99 },
  { id: 3, name: "French Fries", price: 3.99 },
  { id: 4, name: "Caesar Salad", price: 6.99 },
  { id: 5, name: "Orange Juice", price: 2.99 },
  { id: 6, name: "Coffee", price: 2.49 },
];

export default function DineInPage() {
  const [selectedTable, setSelectedTable] = useState(null);
  const [cart, setCart] = useState([]);

  const visibleTables = selectedTable ? [selectedTable] : tables;

  const addToCart = (item) => {
    setCart((prevCart) => {
      const existingItem = prevCart.find((cartItem) => cartItem.id === item.id);

      if (existingItem) {
        return prevCart.map((cartItem) =>
          cartItem.id === item.id
            ? { ...cartItem, quantity: cartItem.quantity + 1 }
            : cartItem
        );
      }

      return [...prevCart, { ...item, quantity: 1 }];
    });
  };

  const cartTotal = cart.reduce(
    (total, item) => total + item.price * item.quantity,
    0
  );

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
                  setSelectedTable(null);
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
                    if (!isOccupied) {
                      setSelectedTable(table);
                    }
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
                  className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <div>
                    <p className="font-bold text-slate-800">{item.name}</p>
                    <p className="text-sm text-slate-500">
                      ${item.price.toFixed(2)} × {item.quantity}
                    </p>
                  </div>

                  <p className="font-black text-slate-900">
                    ${(item.price * item.quantity).toFixed(2)}
                  </p>
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
                  ${item.price.toFixed(2)}
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
      )}
    </div>
  );
}
