import React, { useState } from "react";
import {
  User,
  Phone,
  ShoppingCart,
  Plus,
  Minus,
  Search,
  Loader2,
  Trash2,
  Send,
} from "lucide-react";

const TakeOutPage = ({ products, onSendOrder }) => {
  const [customerName, setCustomerName] = useState("");
  const [customerPhone, setCustomerPhone] = useState("");
  const [cart, setCart] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Filter products based on search
  const filteredProducts = products.filter((p) =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const addToCart = (product) => {
    setCart((prev) => {
      const existing = prev.find((item) => item.id === product.id);
      if (existing) {
        return prev.map((item) =>
          item.id === product.id
            ? { ...item, quantity: item.quantity + 1 }
            : item
        );
      }
      return [...prev, { ...product, quantity: 1 }];
    });
  };

  const removeFromCart = (productId) => {
    setCart((prev) => prev.filter((item) => item.id !== productId));
  };

  const updateQuantity = (productId, delta) => {
    setCart((prev) =>
      prev.map((item) => {
        if (item.id === productId) {
          const newQty = Math.max(1, item.quantity + delta);
          return { ...item, quantity: newQty };
        }
        return item;
      })
    );
  };

  const calculateTotal = () => {
    return cart.reduce(
      (sum, item) => sum + parseFloat(item.base_price) * item.quantity,
      0
    );
  };

  const handleSubmit = async () => {
    if (cart.length === 0) return alert("Cart is empty");

    setIsSubmitting(true);
    try {
      const payload = {
        customer: customerName || "Walk-in Customer",
        customer_phone: customerPhone,
        order_type: "TAKE_OUT",
        total_amount: calculateTotal(),
        items: cart.map((item) => ({
          product: item.id,
          quantity: item.quantity,
          unit_price: parseFloat(item.base_price),
          subtotal: parseFloat(item.base_price) * item.quantity,
        })),
      };

      await onSendOrder(payload);
      setCart([]);
      setCustomerName("");
      setCustomerPhone("");
    } catch (err) {
      // Error handled by parent POS.jsx
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-160px)]">
      {/* Left: Product Selection */}
      <div className="lg:col-span-2 flex flex-col gap-4 overflow-hidden">
        <div className="relative">
          <Search
            className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
            size={20}
          />
          <input
            type="text"
            placeholder="Search products..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-12 pr-4 py-4 bg-white border border-slate-200 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none font-bold"
          />
        </div>

        <div className="flex-1 overflow-y-auto grid grid-cols-2 sm:grid-cols-3 gap-4 pr-2">
          {filteredProducts.map((product) => (
            <button
              key={product.id}
              onClick={() => addToCart(product)}
              className="bg-white p-4 rounded-[24px] border border-slate-200 hover:border-indigo-500 transition-all text-left flex flex-col justify-between group active:scale-95">
              <h3 className="font-bold text-slate-800 mb-2">{product.name}</h3>
              <div className="flex justify-between items-center">
                <span className="text-indigo-600 font-black">
                  ${parseFloat(product.base_price).toFixed(2)}
                </span>
                <div className="w-8 h-8 bg-slate-50 rounded-xl flex items-center justify-center text-slate-400 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                  <Plus size={18} />
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Right: Checkout Sidebar */}
      <div className="bg-white rounded-[32px] shadow-xl border border-slate-100 flex flex-col overflow-hidden">
        <div className="p-6 border-b border-slate-50">
          <h2 className="text-xl font-black text-slate-900 mb-4">
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
                onChange={(e) => setCustomerName(e.target.value)}
                className="w-full pl-10 pr-4 py-3 bg-slate-50 border-none rounded-xl text-sm font-bold"
              />
            </div>
            <div className="relative">
              <Phone
                className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                size={16}
              />
              <input
                type="text"
                placeholder="Phone (Optional)"
                value={customerPhone}
                onChange={(e) => setCustomerPhone(e.target.value)}
                className="w-full pl-10 pr-4 py-3 bg-slate-50 border-none rounded-xl text-sm font-bold"
              />
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {cart.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-slate-400 opacity-50">
              <ShoppingCart
                size={48}
                className="mb-2"
              />
              <p className="font-bold">Cart is empty</p>
            </div>
          ) : (
            cart.map((item) => (
              <div
                key={item.id}
                className="flex justify-between items-center gap-2">
                <div className="flex-1">
                  <p className="text-sm font-bold text-slate-800 leading-tight">
                    {item.name}
                  </p>
                  <p className="text-xs text-indigo-600 font-black">
                    ${parseFloat(item.base_price).toFixed(2)}
                  </p>
                </div>
                <div className="flex items-center gap-3 bg-slate-50 p-1 rounded-xl">
                  <button
                    onClick={() => updateQuantity(item.id, -1)}
                    className="p-1 hover:bg-white rounded-lg transition-colors">
                    <Minus size={14} />
                  </button>
                  <span className="text-sm font-black w-4 text-center">
                    {item.quantity}
                  </span>
                  <button
                    onClick={() => updateQuantity(item.id, 1)}
                    className="p-1 hover:bg-white rounded-lg transition-colors">
                    <Plus size={14} />
                  </button>
                </div>
                <button
                  onClick={() => removeFromCart(item.id)}
                  className="text-slate-300 hover:text-red-500 transition-colors">
                  <Trash2 size={16} />
                </button>
              </div>
            ))
          )}
        </div>

        <div className="p-6 bg-slate-900 text-white">
          <div className="flex justify-between items-center mb-4">
            <span className="text-slate-400 text-xs font-bold uppercase">
              Total Amount
            </span>
            <span className="text-2xl font-black">
              ${calculateTotal().toFixed(2)}
            </span>
          </div>
          <button
            onClick={handleSubmit}
            disabled={isSubmitting || cart.length === 0}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-4 rounded-2xl font-black flex items-center justify-center gap-2 transition-all disabled:opacity-50">
            {isSubmitting ? (
              <Loader2 className="animate-spin" />
            ) : (
              <Send size={20} />
            )}
            PLACE ORDER
          </button>
        </div>
      </div>
    </div>
  );
};

export default TakeOutPage;
