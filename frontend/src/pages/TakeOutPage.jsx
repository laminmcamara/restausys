import React, { useState } from "react";

const menus = [
  { id: 1, name: "Chicken Burger", price: 8.99 },
  { id: 2, name: "Beef Burger", price: 9.99 },
  { id: 3, name: "French Fries", price: 3.99 },
  { id: 4, name: "Caesar Salad", price: 6.99 },
  { id: 5, name: "Orange Juice", price: 2.99 },
  { id: 6, name: "Coffee", price: 2.49 },
];

export default function TakeOutPage() {
  const [cart, setCart] = useState([]);

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
    <div className="grid gap-6 lg:grid-cols-3">
      <section className="rounded-3xl bg-white p-6 shadow-sm lg:col-span-2">
        <h1 className="text-3xl font-black text-slate-900">Take-out</h1>
        <p className="mt-1 text-sm text-slate-500">
          Add menu items directly to the take-out cart.
        </p>

        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
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

      <aside className="rounded-3xl bg-white p-6 shadow-sm">
        <h2 className="text-xl font-black text-slate-900">Take-out Cart</h2>

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
            disabled={cart.length === 0}
            className="mt-5 w-full rounded-xl bg-blue-600 px-4 py-3 font-black text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300">
            Send Order
          </button>
        </div>
      </aside>
    </div>
  );
}
