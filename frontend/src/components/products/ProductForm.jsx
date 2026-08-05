import React, { useState } from "react";
import { createProduct } from "../../services/productService";

const ProductForm = ({
  categories = [],
  modifierGroups = [],
  token,
  onProductCreated,
}) => {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [basePrice, setBasePrice] = useState("");
  const [category, setCategory] = useState("");
  const [isAvailable, setIsAvailable] = useState(true);
  const [image, setImage] = useState(null);
  const [selectedGroups, setSelectedGroups] = useState([]);

  const handleGroupToggle = (groupId) => {
    setSelectedGroups((prev) =>
      prev.includes(groupId)
        ? prev.filter((id) => id !== groupId)
        : [...prev, groupId]
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const formData = new FormData();
    formData.append("name", name);
    formData.append("description", description);
    formData.append("base_price", basePrice);
    formData.append("category", category);
    formData.append("is_available", isAvailable);

    // ✅ Append modifier groups (ManyToMany)
    selectedGroups.forEach((groupId) => {
      formData.append("modifier_groups", groupId);
    });

    if (image) {
      formData.append("image", image);
    }

    try {
      await createProduct(formData, token);

      // ✅ Reset form
      setName("");
      setDescription("");
      setBasePrice("");
      setCategory("");
      setIsAvailable(true);
      setImage(null);
      setSelectedGroups([]);

      onProductCreated();
    } catch (error) {
      console.error("Error creating product:", error);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      style={{ marginBottom: "30px" }}>
      <h2>Create Product</h2>

      {/* Product Name */}
      <input
        type="text"
        placeholder="Product Name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        required
      />
      <br />

      {/* Description */}
      <textarea
        placeholder="Description"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />
      <br />

      {/* Base Price */}
      <input
        type="number"
        step="0.01"
        placeholder="Base Price"
        value={basePrice}
        onChange={(e) => setBasePrice(e.target.value)}
        required
      />
      <br />

      {/* Category */}
      <select
        value={category}
        onChange={(e) => setCategory(e.target.value)}
        required>
        <option value="">Select Category</option>
        {categories.map((cat) => (
          <option
            key={cat.id}
            value={cat.id}>
            {cat.name}
          </option>
        ))}
      </select>
      <br />

      {/* Modifier Groups */}
      <h4>Modifier Groups</h4>
      {modifierGroups.length === 0 && <p>No modifier groups available.</p>}
      {modifierGroups.map((group) => (
        <label
          key={group.id}
          style={{ display: "block" }}>
          <input
            type="checkbox"
            checked={selectedGroups.includes(group.id)}
            onChange={() => handleGroupToggle(group.id)}
          />
          {group.name}
        </label>
      ))}
      <br />

      {/* Availability */}
      <label>
        <input
          type="checkbox"
          checked={isAvailable}
          onChange={(e) => setIsAvailable(e.target.checked)}
        />
        Available
      </label>
      <br />

      {/* Image Upload */}
      <input
        type="file"
        accept="image/*"
        onChange={(e) => setImage(e.target.files[0])}
      />
      <br />
      <br />

      <button type="submit">Create Product</button>
    </form>
  );
};

export default ProductForm;
