import { useState } from "react";
import { useNavigate } from "react-router-dom";

function RegisterRestaurant() {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    restaurant_name: "",
    email: "",
    password: "",
  });

  const [successMessage, setSuccessMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleChange = (event) => {
    const { name, value } = event.target;

    setFormData((previousData) => ({
      ...previousData,
      [name]: value,
    }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    setSuccessMessage("");
    setErrorMessage("");
    setIsSubmitting(true);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/api/v1/restaurants/register/",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(formData),
        }
      );

      const data = await response.json();

      console.log("REGISTRATION RESPONSE:", data);

      if (!response.ok) {
        setErrorMessage(data.message || data.detail || "Registration failed.");
        return;
      }

      localStorage.setItem("access", data.access);
      localStorage.setItem("refresh", data.refresh);

      localStorage.setItem("company", JSON.stringify(data.company));

      localStorage.setItem("restaurant", JSON.stringify(data.restaurant));

      localStorage.setItem("user", JSON.stringify(data.user));

      setSuccessMessage(data.message || "Registration successful.");

      setTimeout(() => {
        navigate("/dashboard", {
          replace: true,
          state: {
            registrationMessage: data.message || "Registration successful.",
          },
        });
      }, 2500);
    } catch (error) {
      console.error("REGISTRATION ERROR:", error);

      setErrorMessage("Unable to connect to the server.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="register-page">
      <h1>Register your restaurant</h1>

      {successMessage && (
        <div
          className="success-message"
          role="alert">
          {successMessage}
        </div>
      )}

      {errorMessage && (
        <div
          className="error-message"
          role="alert">
          {errorMessage}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="restaurant_name">Restaurant name</label>

          <input
            id="restaurant_name"
            name="restaurant_name"
            type="text"
            value={formData.restaurant_name}
            onChange={handleChange}
            required
          />
        </div>

        <div>
          <label htmlFor="email">Email</label>

          <input
            id="email"
            name="email"
            type="email"
            value={formData.email}
            onChange={handleChange}
            required
          />
        </div>

        <div>
          <label htmlFor="password">Password</label>

          <input
            id="password"
            name="password"
            type="password"
            value={formData.password}
            onChange={handleChange}
            required
          />
        </div>

        <button
          type="submit"
          disabled={isSubmitting}>
          {isSubmitting ? "Creating account..." : "Register"}
        </button>
      </form>
    </div>
  );
}

export default RegisterRestaurant;
