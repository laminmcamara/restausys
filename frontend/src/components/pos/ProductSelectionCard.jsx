import React, { useState } from "react";

const ProductSelectionCard = ({ product }) => {
  const [selectedOptions, setSelectedOptions] = useState({});

  const basePrice = parseFloat(product.base_price);

  const calculateTotal = () => {
    let total = basePrice;

    Object.values(selectedOptions).forEach((options) => {
      options.forEach((opt) => {
        total += parseFloat(opt.price_adjustment);
      });
    });

    return total.toFixed(2);
  };

  const handleSelect = (group, option) => {
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

  return (
    <div className="border p-4 rounded bg-white">
      <h2 className="text-xl font-semibold">{product.name}</h2>
      <p className="mb-4">${product.base_price}</p>

      {product.modifier_groups?.map((group) => (
        <div
          key={group.id}
          className="mb-4">
          <h3 className="font-medium">{group.name}</h3>

          {group.options.map((option) => (
            <label
              key={option.id}
              className="block">
              <input
                type={group.selection_type === "SINGLE" ? "radio" : "checkbox"}
                name={group.id}
                onChange={() => handleSelect(group, option)}
              />
              {option.name} (+{option.price_adjustment})
            </label>
          ))}
        </div>
      ))}

      <h3 className="text-lg font-bold">Total: ${calculateTotal()}</h3>
    </div>
  );
};

export default ProductSelectionCard;
