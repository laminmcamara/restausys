import React, { useEffect, useState } from "react";
import api from "../services/api";
import POSProductModal from "./POSProductModal";
import {
  ShoppingCart,
  Trash2,
  ArrowLeft,
  Users,
  Loader2,
  Plus,
} from "lucide-react";

export default function POS() {
  const [view, setView] = useState("tables");
  const [selectedTable, setSelectedTable] = useState(null);
  const [tables, setTables] = useState([]);
  const [categories, setCategories] = useState([]);
  const [products, setProducts] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [cart, setCart] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [activeProduct, setActiveProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [issubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    setLoading(true);
    try {
      const [tableRes, catRes, prodRes] = await Promise.all([
        api.get("/tables/"),
        api.get("/manager/categories/"),
        api.get("/manager/products/"),
      ]);
      setTables(tableRes.data.results || tableRes.data);
      setCategories(catRes.data.results || catRes.data);
      setProducts(prodRes.data.results || prodRes.data);
      if (catRes.data.length > 0) setSelectedCategory(catRes.data[0].id);
    } catch (err) {
      console.error("Failed to fetch POS data", err);
    } finally {
      setLoading(false);
    }
  };

  const handleTableSelect = (table) => {
    setSelectedTable(table);
    setView("menu");
  };

  const addToCart = (itemWithModifiers) => {
    const modifierKey = itemWithModifiers.selectedModifiers
      .map((m) => m.id)
      .sort()
      .join("-");
    const cartItemId = `${itemWithModifiers.id}-${modifierKey}`;
    setCart((prev) => {
      const existingIndex = prev.findIndex(
        (item) => item.cartItemId === cartItemId
      );
      if (existingIndex > -1) {
        const newCart = [...prev];
        newCart[existingIndex].quantity += itemWithModifiers.quantity;
        return newCart;
      }
      return [...prev, { ...itemWithModifiers, cartItemId }];
    });
  };

  const handlePlaceOrder = async () => {
    if (cart.length === 0) return;
    setIsSubmitting(true);
    try {
      const orderData = {
        table_id: selectedTable.id,
        items: cart.map((item) => ({
          product_id: item.id,
          quantity: item.quantity,
          modifier_option_ids: item.selectedModifiers.map((m) => m.id),
          unit_price: item.finalPrice,
        })),
      };
      await api.post("/orders/place/", orderData);
      alert("Order placed successfully!");
      setCart([]);
      setView("tables");
      fetchInitialData();
    } catch (err) {
      alert(err.response?.data?.error || "Failed to place order.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const calculateTotal = () =>
    cart.reduce((sum, item) => sum + item.finalPrice * item.quantity, 0);
  const filteredProducts = selectedCategory
    ? products.filter(
        (p) => (p.category?.id || p.category) === selectedCategory
      )
    : products;

  if (loading)
    return (
      <div className="h-screen flex items-center justify-center bg-white">
        <Loader2
          className="animate-spin text-blue-600"
          size={40}
        />
      </div>
    );

  if (view === "tables") {
    return (
      <div className="p-6 bg-gray-50 min-h-screen">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-black text-gray-900 mb-6">Floor Plan</h1>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {tables.map((table) => (
              <button
                key={table.id}
                onClick={() => handleTableSelect(table)}
                className={`h-32 rounded-2xl transition-all border-2 flex flex-col items-center justify-center ${
                  table.has_active_session
                    ? "border-orange-400 bg-orange-50"
                    : "border-white bg-white shadow-sm hover:border-blue-400"
                }`}>
                <span className="text-2xl font-black text-gray-800">
                  {table.table_number}
                </span>
                <div className="flex items-center gap-1 text-gray-400 text-xs mt-1">
                  <Users size={14} /> {table.capacity}
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-100 overflow-hidden">
      {/* Main Product Area - Expanded */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="bg-white border-b px-4 py-3 flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setView("tables")}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors">
              <ArrowLeft size={20} />
            </button>
            <div>
              <h2 className="text-lg font-bold leading-tight">
                Table {selectedTable?.table_number}
              </h2>
              <p className="text-xs text-gray-500">New Order</p>
            </div>
          </div>
          <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
            {categories.map((cat) => (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.id)}
                className={`px-4 py-1.5 rounded-full font-bold text-xs whitespace-nowrap transition-all ${
                  selectedCategory === cat.id
                    ? "bg-blue-600 text-white shadow-md"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}>
                {cat.name}
              </button>
            ))}
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-4 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
          {filteredProducts.map((product) => (
            <button
              key={product.id}
              onClick={() => {
                setActiveProduct(product);
                setIsModalOpen(true);
              }}
              className="bg-white p-4 rounded-2xl shadow-sm border border-transparent hover:border-blue-500 transition-all text-left flex flex-col justify-between group h-36">
              <div>
                <h3 className="font-bold text-gray-800 text-sm line-clamp-2 group-hover:text-blue-600">
                  {product.name}
                </h3>
              </div>
              <div className="flex justify-between items-end">
                <span className="text-lg font-black text-gray-900">
                  ${parseFloat(product.base_price).toFixed(2)}
                </span>
                <div className="bg-blue-50 p-1.5 rounded-lg text-blue-600 group-hover:bg-blue-600 group-hover:text-white transition-colors">
                  <Plus size={16} />
                </div>
              </div>
            </button>
          ))}
        </main>
      </div>

      {/* Cart Sidebar - Narrower (w-80 = 320px) */}
      <aside className="w-80 bg-white border-l flex flex-col shadow-xl">
        <div className="p-4 border-b bg-gray-50/50">
          <h2 className="text-lg font-bold flex items-center gap-2">
            <ShoppingCart size={18} /> Cart
            <span className="ml-auto bg-blue-100 text-blue-600 px-2 py-0.5 rounded-md text-xs">
              {cart.length} items
            </span>
          </h2>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {cart.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-gray-300 italic py-20">
              <ShoppingCart
                size={48}
                className="mb-2 opacity-20"
              />
              <p className="text-sm">Empty cart</p>
            </div>
          ) : (
            cart.map((item) => (
              <div
                key={item.cartItemId}
                className="group border-b border-gray-50 pb-3">
                <div className="flex justify-between items-start mb-1">
                  <div className="flex-1">
                    <p className="text-sm font-bold text-gray-800 leading-tight">
                      {item.quantity}x {item.name}
                    </p>
                    {item.selectedModifiers.map((m) => (
                      <p
                        key={m.id}
                        className="text-[10px] text-gray-500 ml-2">
                        • {m.name}
                      </p>
                    ))}
                  </div>
                  <span className="text-sm font-bold text-gray-900 ml-2">
                    ${(item.finalPrice * item.quantity).toFixed(2)}
                  </span>
                </div>
                <button
                  onClick={() =>
                    setCart(
                      cart.filter((i) => i.cartItemId !== item.cartItemId)
                    )
                  }
                  className="text-red-400 text-[10px] flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity hover:text-red-600">
                  <Trash2 size={10} /> Remove
                </button>
              </div>
            ))
          )}
        </div>

        <div className="p-4 bg-gray-50 border-t space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-gray-500 text-sm font-medium">Subtotal</span>
            <span className="text-gray-900 font-bold">
              ${calculateTotal().toFixed(2)}
            </span>
          </div>
          <div className="flex justify-between items-center text-xl font-black border-t pt-2">
            <span>Total</span>
            <span className="text-blue-600">
              ${calculateTotal().toFixed(2)}
            </span>
          </div>
          <button
            onClick={handlePlaceOrder}
            disabled={cart.length === 0 || issubmitting}
            className="w-full bg-blue-600 text-white py-4 rounded-xl font-bold text-md shadow-lg hover:bg-blue-700 active:scale-[0.98] transition-all disabled:bg-gray-200 disabled:text-gray-400 disabled:shadow-none flex justify-center items-center gap-2">
            {issubmitting ? (
              <Loader2
                className="animate-spin"
                size={20}
              />
            ) : (
              "Send to Kitchen"
            )}
          </button>
        </div>
      </aside>

      <POSProductModal
        isOpen={isModalOpen}
        product={activeProduct}
        onClose={() => setIsModalOpen(false)}
        onAddToCart={addToCart}
      />
    </div>
  );
}
