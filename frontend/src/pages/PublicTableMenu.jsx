import React, { useEffect, useMemo, useState } from "react";

import { useParams } from "react-router-dom";

import api from "../services/api";

const formatCurrency = (value) => {
  const amount = Number(value);

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(Number.isFinite(amount) ? amount : 0);
};

export default function PublicTableMenu() {
  const { token } = useParams();

  const [menu, setMenu] = useState(null);

  const [cart, setCart] = useState({});

  const [loading, setLoading] = useState(true);

  const [submitting, setSubmitting] = useState(false);

  const [error, setError] = useState("");

  const [success, setSuccess] = useState("");

  useEffect(() => {
    let mounted = true;

    const fetchMenu = async () => {
      try {
        const response = await api.get(`/public/tables/${token}/menu/`);

        if (mounted) {
          setMenu(response.data);
        }
      } catch (requestError) {
        if (mounted) {
          setError(
            requestError?.response?.data?.detail || "Unable to load menu."
          );
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    fetchMenu();

    return () => {
      mounted = false;
    };
  }, [token]);

  const products = useMemo(() => {
    if (!menu?.categories) {
      return [];
    }

    return menu.categories.flatMap((category) => category.products || []);
  }, [menu]);

  const cartItems = useMemo(() => {
    return Object.entries(cart)
      .map(([productId, quantity]) => {
        const product = products.find(
          (item) => String(item.id) === String(productId)
        );

        if (!product) {
          return null;
        }

        return {
          product,
          quantity,
          total: Number(product.price || 0) * quantity,
        };
      })
      .filter(Boolean);
  }, [cart, products]);

  const cartTotal = cartItems.reduce((total, item) => total + item.total, 0);

  const addProduct = (product) => {
    setCart((current) => ({
      ...current,
      [product.id]: (current[product.id] || 0) + 1,
    }));
  };

  const removeProduct = (product) => {
    setCart((current) => {
      const next = {
        ...current,
      };

      const quantity = next[product.id] || 0;

      if (quantity <= 1) {
        delete next[product.id];
      } else {
        next[product.id] = quantity - 1;
      }

      return next;
    });
  };

  const submitOrder = async () => {
    if (!cartItems.length) {
      setError("Add at least one item.");
      return;
    }

    setSubmitting(true);
    setError("");
    setSuccess("");

    try {
      const response = await api.post(`/public/tables/${token}/orders/`, {
        order_type: "DINE_IN",
        items: cartItems.map((item) => ({
          product: item.product.id,
          quantity: item.quantity,
          modifiers: [],
        })),
      });

      setCart({});

      setSuccess(
        `Order #${response.data.order.order_number} sent to the restaurant.`
      );
    } catch (requestError) {
      setError(
        requestError?.response?.data?.detail || "Unable to submit order."
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <div className="p-10 text-center">Loading menu...</div>;
  }

  if (error && !menu) {
    return <div className="p-10 text-center text-red-600">{error}</div>;
  }

  return (
    <div className="min-h-screen bg-slate-50 p-4">
      <div className="max-w-6xl mx-auto">
        <header className="bg-white rounded-3xl p-6 mb-6 shadow-sm">
          <h1 className="text-3xl font-black text-slate-900">
            {menu?.table?.restaurant_name}
          </h1>

          <p className="text-slate-500 font-bold mt-1">
            Table {menu?.table?.table_number}
          </p>
        </header>

        {error && (
          <div className="mb-4 bg-red-50 text-red-700 p-4 rounded-xl font-bold">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-4 bg-emerald-50 text-emerald-700 p-4 rounded-xl font-bold">
            {success}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <main className="lg:col-span-2 space-y-6">
            {menu?.categories?.map((category) => (
              <section
                key={String(category.id)}
                className="bg-white rounded-3xl p-5 shadow-sm">
                <h2 className="text-xl font-black text-slate-900 mb-4">
                  {category.name}
                </h2>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {category.products?.map((product) => {
                    const quantity = cart[product.id] || 0;

                    return (
                      <div
                        key={String(product.id)}
                        className="border border-slate-200 rounded-2xl p-4">
                        <h3 className="font-black text-slate-900">
                          {product.name}
                        </h3>

                        <p className="text-sm text-slate-500 mt-1">
                          {product.description}
                        </p>

                        <div className="flex justify-between items-center mt-4">
                          <span className="font-black text-indigo-600">
                            {formatCurrency(product.price)}
                          </span>

                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              onClick={() => {
                                removeProduct(product);
                              }}
                              disabled={quantity === 0}
                              className="w-8 h-8 rounded-lg bg-slate-100 font-black disabled:opacity-40">
                              −
                            </button>

                            <span className="w-6 text-center font-black">
                              {quantity}
                            </span>

                            <button
                              type="button"
                              onClick={() => {
                                addProduct(product);
                              }}
                              className="w-8 h-8 rounded-lg bg-indigo-600 text-white font-black">
                              +
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            ))}
          </main>

          <aside className="bg-white rounded-3xl p-5 shadow-sm h-fit sticky top-4">
            <h2 className="text-xl font-black text-slate-900">Your Order</h2>

            <div className="mt-4 space-y-3">
              {cartItems.length === 0 ? (
                <p className="text-slate-400 italic">Your cart is empty.</p>
              ) : (
                cartItems.map((item) => (
                  <div
                    key={String(item.product.id)}
                    className="flex justify-between gap-3">
                    <span className="font-bold text-slate-700">
                      {item.quantity} × {item.product.name}
                    </span>

                    <span className="font-black">
                      {formatCurrency(item.total)}
                    </span>
                  </div>
                ))
              )}
            </div>

            <div className="border-t mt-5 pt-5 flex justify-between">
              <span className="font-black">Total</span>

              <span className="font-black text-xl">
                {formatCurrency(cartTotal)}
              </span>
            </div>

            <button
              type="button"
              onClick={submitOrder}
              disabled={submitting || cartItems.length === 0}
              className="w-full mt-5 py-4 rounded-2xl bg-indigo-600 text-white font-black disabled:opacity-50">
              {submitting ? "Sending..." : "Send Order"}
            </button>
          </aside>
        </div>
      </div>
    </div>
  );
}
