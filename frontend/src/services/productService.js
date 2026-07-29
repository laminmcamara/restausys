const API_BASE = "http://127.0.0.1:8000/api/v1";

export const fetchProducts = async (token) => {
  const response = await fetch(`${API_BASE}/manager/products/`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error("Failed to fetch products");
  }

  return response.json();
};

export const fetchCategories = async (token) => {
  const response = await fetch(`${API_BASE}/categories/`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error("Failed to fetch categories");
  }

  return response.json();
};

export const createProduct = async (formData, token) => {
  const response = await fetch(`${API_BASE}/manager/products/`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    console.log(error);
    throw new Error("Failed to create product");
  }

  return response.json();
};