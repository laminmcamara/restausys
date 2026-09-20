import React, { useMemo, useState } from "react";

import {
  Loader2,
  Minus,
  Phone,
  Plus,
  Search,
  Send,
  ShoppingCart,
  Trash2,
  User,
} from "lucide-react";

const MAX_QUANTITY_PER_ITEM = 50;

const getProductPrice = (product) => {
  const value = Number(product?.price ?? product?.base_price ?? 0);

  return Number.isFinite(value) ? value : 0;
};

const getProductName = (product) => {
  return product?.name || product?.product_name || "Unnamed product";
};

const getProductCategoryId = (product) => {
  return (
    product?.category?.id ?? product?.category_id ?? product?.category ?? null
  );
};

const isProductAvailable = (product) => {
  return product?.is_available !== false;
};

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

const TakeOutPage = ({ products = [], onSendOrder }) => {
  const [customerName, setCustomerName] = useState("");

  const [customerPhone, setCustomerPhone] = useState("");

  const [cart, setCart] = useState([]);

  const [searchQuery, setSearchQuery] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);

  const [error, setError] = useState("");

  const safeProducts = useMemo(() => {
    if (!Array.isArray(products)) {
      return [];
    }

    return products.map((product) => ({
      ...product,
      display_name: getProductName(product),
      display_price: getProductPrice(product),
      category_id: getProductCategoryId(product),
    }));
  }, [products]);

  const filteredProducts = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();

    return safeProducts.filter((product) => {
      const productName = product.display_name.toLowerCase();

      const description = String(product?.description || "").toLowerCase();

      return (
        isProductAvailable(product) &&
        (!query || productName.includes(query) || description.includes(query))
      );
    });
  }, [safeProducts, searchQuery]);

  const addToCart = (product) => {
    if (!isProductAvailable(product)) {
      setError("This product is not available.");
      return;
    }

    setError("");

    setCart((currentCart) => {
      const existingItem = currentCart.find((item) => item.id === product.id);

      if (existingItem) {
        const nextQuantity = existingItem.quantity + 1;

        if (nextQuantity > MAX_QUANTITY_PER_ITEM) {
          setError(`Maximum quantity is ${MAX_QUANTITY_PER_ITEM} per item.`);

          return currentCart;
        }

        return currentCart.map((item) =>
          item.id === product.id
            ? {
                ...item,
                quantity: nextQuantity,
              }
            : item
        );
      }

      return [
        ...currentCart,
        {
          ...product,
          quantity: 1,
          unit_price: product.display_price,
        },
      ];
    });
  };

  const removeFromCart = (productId) => {
    setCart((currentCart) =>
      currentCart.filter((item) => item.id !== productId)
    );
  };

  const updateQuantity = (productId, delta) => {
    setCart((currentCart) =>
      currentCart
        .map((item) => {
          if (item.id !== productId) {
            return item;
          }

          const nextQuantity = item.quantity + delta;

          return {
            ...item,
            quantity: Math.min(
              MAX_QUANTITY_PER_ITEM,
              Math.max(0, nextQuantity)
            ),
          };
        })
        .filter((item) => item.quantity > 0)
    );
  };

  const calculateTotal = () => {
    return cart.reduce((sum, item) => {
      const price = Number(
        item.display_price ??
          item.unit_price ??
          item.price ??
          item.base_price ??
          0
      );

      const quantity = Number(item.quantity || 0);

      return sum + (Number.isFinite(price) ? price : 0) * quantity;
    }, 0);
  };

  const handleSubmit = async () => {
    if (cart.length === 0) {
      setError("Add at least one product.");
      return;
    }

    if (typeof onSendOrder !== "function") {
      setError("Take-out order handler is unavailable.");
      return;
    }

    const invalidItem = cart.find(
      (item) =>
        !item.id ||
        !Number.isInteger(Number(item.quantity)) ||
        Number(item.quantity) < 1 ||
        Number(item.quantity) > MAX_QUANTITY_PER_ITEM
    );

    if (invalidItem) {
      setError("One or more cart items have an invalid quantity.");
      return;
    }

    setError("");
    setIsSubmitting(true);

    try {
      await onSendOrder(cart, {
        customer_name: customerName.trim() || "Walk-in Customer",
        customer_phone: customerPhone.trim(),
      });

      setCart([]);
      setCustomerName("");
      setCustomerPhone("");
    } catch (requestError) {
      console.error("Take-out submission error:", requestError);

      setError(getErrorMessage(requestError, "Take-out order failed."));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="grid h-[calc(100vh-160px)] grid-cols-1 gap-6 lg:grid-cols-3">
      <div className="flex flex-col gap-4 overflow-hidden lg:col-span-2">
        <div className="relative">
          <Search
            className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
            size={20}
          />

          <input
            type="text"
            placeholder="Search products..."
            value={searchQuery}
            onChange={(event) => {
              setSearchQuery(event.target.value);
            }}
            className="w-full rounded-2xl border border-slate-200 bg-white py-4 pl-12 pr-4 font-bold outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">
            {error}
          </div>
        )}

        <div className="grid flex-1 grid-cols-2 gap-4 overflow-y-auto pr-2 sm:grid-cols-3">
          {filteredProducts.length === 0 ? (
            <div className="col-span-full flex min-h-[200px] items-center justify-center rounded-3xl border-2 border-dashed border-slate-200 bg-white text-sm font-bold text-slate-400">
              No available products found.
            </div>
          ) : (
            filteredProducts.map((product) => (
              <button
                key={String(product.id)}
                type="button"
                onClick={() => {
                  addToCart(product);
                }}
                disabled={!isProductAvailable(product)}
                className="group flex min-h-[140px] flex-col justify-between rounded-[24px] border border-slate-200 bg-white p-4 text-left transition-all hover:border-indigo-500 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50">
                <div>
                  <h3 className="mb-2 font-bold text-slate-800">
                    {product.display_name}
                  </h3>

                  {product.description && (
                    <p className="line-clamp-2 text-xs text-slate-400">
                      {product.description}
                    </p>
                  )}
                </div>

                <div className="mt-4 flex items-center justify-between">
                  <span className="font-black text-indigo-600">
                    ${product.display_price.toFixed(2)}
                  </span>

                  <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-slate-50 text-slate-400 transition-colors group-hover:bg-indigo-600 group-hover:text-white">
                    <Plus size={18} />
                  </div>
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      <div className="flex flex-col overflow-hidden rounded-[32px] border border-slate-100 bg-white shadow-xl">
        <div className="border-b border-slate-50 p-6">
          <h2 className="mb-4 text-xl font-black text-slate-900">
            Take-Out Details
          </h2>

          <div className="space-y-3">
            <div className="relative">
              <User
                className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                size={16}
              />

              <input
                type="text"
                placeholder="Customer Name"
                value={customerName}
                onChange={(event) => {
                  setCustomerName(event.target.value);
                }}
                className="w-full rounded-xl bg-slate-50 py-3 pl-10 pr-4 text-sm font-bold outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div className="relative">
              <Phone
                className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                size={16}
              />

              <input
                type="tel"
                placeholder="Phone (Optional)"
                value={customerPhone}
                onChange={(event) => {
                  setCustomerPhone(event.target.value);
                }}
                className="w-full rounded-xl bg-slate-50 py-3 pl-10 pr-4 text-sm font-bold outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto p-6">
          {cart.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center text-slate-400 opacity-50">
              <ShoppingCart
                size={48}
                className="mb-2"
              />

              <p className="font-bold">Cart is empty</p>
            </div>
          ) : (
            cart.map((item) => (
              <div
                key={String(item.id)}
                className="flex items-center justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-bold leading-tight text-slate-800">
                    {getProductName(item)}
                  </p>

                  <p className="font-black text-indigo-600">
                    $
                    {Number(item.display_price ?? item.unit_price ?? 0).toFixed(
                      2
                    )}
                  </p>
                </div>

                <div className="flex items-center gap-3 rounded-xl bg-slate-50 p-1">
                  <button
                    type="button"
                    onClick={() => {
                      updateQuantity(item.id, -1);
                    }}
                    disabled={isSubmitting}
                    className="rounded-lg p-1 transition-colors hover:bg-white disabled:opacity-50">
                    <Minus size={14} />
                  </button>

                  <span className="w-4 text-center text-sm font-black">
                    {item.quantity}
                  </span>

                  <button
                    type="button"
                    onClick={() => {
                      updateQuantity(item.id, 1);
                    }}
                    disabled={
                      isSubmitting || item.quantity >= MAX_QUANTITY_PER_ITEM
                    }
                    className="rounded-lg p-1 transition-colors hover:bg-white disabled:opacity-50">
                    <Plus size={14} />
                  </button>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    removeFromCart(item.id);
                  }}
                  disabled={isSubmitting}
                  className="text-slate-300 transition-colors hover:text-red-500 disabled:opacity-50">
                  <Trash2 size={16} />
                </button>
              </div>
            ))
          )}
        </div>

        <div className="bg-slate-900 p-6 text-white">
          <div className="mb-4 flex items-center justify-between">
            <span className="text-xs font-bold uppercase text-slate-400">
              Total Amount
            </span>

            <span className="text-2xl font-black">
              ${calculateTotal().toFixed(2)}
            </span>
          </div>

          <button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting || cart.length === 0}
            className="flex w-full items-center justify-center gap-2 rounded-2xl bg-indigo-600 py-4 font-black text-white transition-all hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50">
            {isSubmitting ? (
              <Loader2
                className="animate-spin"
                size={20}
              />
            ) : (
              <Send size={20} />
            )}

            {isSubmitting ? "Creating Order..." : "PLACE ORDER"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default TakeOutPage;
