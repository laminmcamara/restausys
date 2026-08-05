import React, { useState } from "react";
import { createModifierOption } from "../../services/modifierService";

const ModifierOptionForm = ({ groupId, token, onSuccess }) => {
  const [name, setName] = useState("");
  const [priceAdjustment, setPriceAdjustment] = useState(0);
  const [displayOrder, setDisplayOrder] = useState(0);

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      await createModifierOption(
        {
          group: groupId,
          name,
          price_adjustment: priceAdjustment,
          display_order: displayOrder,
        },
        token
      );

      setName("");
      setPriceAdjustment(0);
      setDisplayOrder(0);
      onSuccess();
    } catch (err) {
      console.error(err);
      alert("Failed to create option.");
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="mt-3 border-t pt-3">
      <input
        type="text"
        placeholder="Option Name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        required
        className="border p-2 w-full mb-2 rounded"
      />

      <input
        type="number"
        step="0.01"
        placeholder="Price Adjustment"
        value={priceAdjustment}
        onChange={(e) => setPriceAdjustment(e.target.value)}
        className="border p-2 w-full mb-2 rounded"
      />

      <input
        type="number"
        placeholder="Display Order"
        value={displayOrder}
        onChange={(e) => setDisplayOrder(e.target.value)}
        className="border p-2 w-full mb-2 rounded"
      />

      <button
        type="submit"
        className="bg-green-600 text-white px-3 py-1 rounded">
        Add Option
      </button>
    </form>
  );
};

export default ModifierOptionForm;
