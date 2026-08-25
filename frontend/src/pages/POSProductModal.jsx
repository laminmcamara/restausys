import React, { useState, useEffect } from "react";
import { X, Plus, Minus } from "lucide-react";

const POSProductModal = ({ product, isOpen, onClose, onAddToCart }) => {
  const [quantity, setQuantity] = useState(1);
  const [selectedModifiers, setSelectedModifiers] = useState({});
  const [totalPrice, setTotalPrice] = useState(0);

  // Reset state when product changes
  useEffect(() => {
    if (product) {
      setQuantity(1);
      setSelectedModifiers({});
      setTotalPrice(parseFloat(product.base_price));
    }
  }, [product]);

  // Calculate total price whenever modifiers or quantity change
  useEffect(() => {
    if (!product) return;

    let modifiersCost = 0;
    Object.values(selectedModifiers).forEach((modArray) => {
      modArray.forEach((mod) => {
        modifiersCost += parseFloat(mod.price_adjustment || 0);
      });
    });

    setTotalPrice((parseFloat(product.base_price) + modifiersCost) * quantity);
  }, [selectedModifiers, quantity, product]);

  if (!isOpen || !product) return null;

  const handleModifierToggle = (group, option) => {
    const groupId = group.id;
    const isSingle = group.selection_type === "SINGLE";

    setSelectedModifiers((prev) => {
      const currentSelection = prev[groupId] || [];

      if (isSingle) {
        // If single choice, replace the whole array with just this option
        return { ...prev, [groupId]: [option] };
      } else {
        // If multiple, toggle the option in the array
        const exists = currentSelection.find((item) => item.id === option.id);
        if (exists) {
          return {
            ...prev,
            [groupId]: currentSelection.filter((item) => item.id !== option.id),
          };
        } else {
          return { ...prev, [groupId]: [...currentSelection, option] };
        }
      }
    });
  };

  const handleConfirm = () => {
    // Flatten selected modifiers for the cart
    const flatModifiers = Object.values(selectedModifiers).flat();
    onAddToCart({
      ...product,
      quantity,
      selectedModifiers: flatModifiers,
      finalPrice: totalPrice / quantity, // price per unit with mods
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-white w-full max-w-md rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-4 border-b flex justify-between items-center bg-gray-50">
          <h2 className="text-xl font-bold text-gray-800">{product.name}</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-200 rounded-full transition">
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto flex-1 space-y-6">
          {/* Modifier Groups */}
          {product.modifier_groups?.map((group) => (
            <div
              key={group.id}
              className="space-y-3">
              <div className="flex justify-between items-center">
                <h3 className="font-bold text-gray-700">{group.name}</h3>
                <span className="text-xs text-gray-400 uppercase font-semibold">
                  {group.selection_type === "SINGLE"
                    ? "Pick 1"
                    : "Multi-select"}
                </span>
              </div>
              <div className="grid grid-cols-1 gap-2">
                {group.options?.map((option) => {
                  const isSelected = selectedModifiers[group.id]?.some(
                    (item) => item.id === option.id
                  );
                  return (
                    <button
                      key={option.id}
                      onClick={() => handleModifierToggle(group, option)}
                      className={`flex justify-between items-center p-3 rounded-xl border-2 transition-all ${
                        isSelected
                          ? "border-blue-600 bg-blue-50"
                          : "border-gray-100 hover:border-gray-300"
                      }`}>
                      <span
                        className={`font-medium ${
                          isSelected ? "text-blue-700" : "text-gray-600"
                        }`}>
                        {option.name}
                      </span>
                      <span className="text-sm font-bold text-green-600">
                        +${parseFloat(option.price_adjustment).toFixed(2)}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}

          {/* Quantity Selector */}
          <div className="pt-4 border-t flex justify-between items-center">
            <span className="font-bold text-gray-700">Quantity</span>
            <div className="flex items-center gap-4 bg-gray-100 p-1 rounded-lg">
              <button
                onClick={() => setQuantity(Math.max(1, quantity - 1))}
                className="p-2 bg-white rounded-md shadow-sm hover:text-red-500">
                <Minus size={18} />
              </button>
              <span className="w-8 text-center font-bold text-lg">
                {quantity}
              </span>
              <button
                onClick={() => setQuantity(quantity + 1)}
                className="p-2 bg-white rounded-md shadow-sm hover:text-green-500">
                <Plus size={18} />
              </button>
            </div>
          </div>
        </div>

        {/* Footer / Add Button */}
        <div className="p-4 border-t bg-gray-50">
          <button
            onClick={handleConfirm}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white py-4 rounded-xl font-bold text-lg shadow-lg flex justify-between px-6 items-center transition-transform active:scale-95">
            <span>Add to Order</span>
            <span>${totalPrice.toFixed(2)}</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default POSProductModal;
