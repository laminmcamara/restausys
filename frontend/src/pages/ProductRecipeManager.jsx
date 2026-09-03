import React, { useState, useEffect } from "react";
import { Plus, Trash2, Scale } from "lucide-react";
import api from "../services/api";

const ProductRecipeManager = ({
  productId,
  currentIngredients = [],
  onUpdate,
}) => {
  const [inventoryItems, setInventoryItems] = useState([]);
  const [recipe, setRecipe] = useState(currentIngredients);

  useEffect(() => {
    // Load available inventory items to choose from
    api.get("/manager/inventory/").then((res) => {
      setInventoryItems(
        Array.isArray(res.data) ? res.data : res.data.results || []
      );
    });
  }, []);

  const addIngredient = () => {
    setRecipe([...recipe, { inventory_item: "", quantity_required: 1 }]);
  };

  const removeIngredient = (index) => {
    setRecipe(recipe.filter((_, i) => i !== index));
  };

  const updateIngredient = (index, field, value) => {
    const newRecipe = [...recipe];
    newRecipe[index][field] = value;
    setRecipe(newRecipe);
    onUpdate(newRecipe); // Pass back to parent Product form
  };

  return (
    <div className="mt-6 border-t pt-4">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-sm font-black text-slate-800 uppercase flex items-center gap-2">
          <Scale size={16} /> Recipe / Ingredients
        </h3>
        <button
          type="button"
          onClick={addIngredient}
          className="text-xs bg-slate-900 text-white px-2 py-1 rounded-md font-bold hover:bg-slate-700">
          + Add Ingredient
        </button>
      </div>

      <div className="space-y-2">
        {recipe.map((ing, index) => (
          <div
            key={index}
            className="flex gap-2 items-center bg-slate-50 p-2 rounded-lg border border-slate-100">
            <select
              className="flex-1 text-xs border rounded p-1"
              value={ing.inventory_item}
              onChange={(e) =>
                updateIngredient(index, "inventory_item", e.target.value)
              }>
              <option value="">Select Ingredient...</option>
              {inventoryItems.map((item) => (
                <option
                  key={item.id}
                  value={item.id}>
                  {item.name} ({item.unit})
                </option>
              ))}
            </select>

            <input
              type="number"
              step="0.001"
              placeholder="Qty"
              className="w-20 text-xs border rounded p-1"
              value={ing.quantity_required}
              onChange={(e) =>
                updateIngredient(index, "quantity_required", e.target.value)
              }
            />

            <button
              type="button"
              onClick={() => removeIngredient(index)}
              className="text-red-500 hover:bg-red-50 p-1 rounded">
              <Trash2 size={14} />
            </button>
          </div>
        ))}

        {recipe.length === 0 && (
          <p className="text-[10px] text-slate-400 italic text-center py-2">
            No ingredients mapped. Stock will not be auto-deducted for this
            product.
          </p>
        )}
      </div>
    </div>
  );
};

export default ProductRecipeManager;
