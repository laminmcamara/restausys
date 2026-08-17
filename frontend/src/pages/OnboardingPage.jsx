import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Building2,
  CheckCircle2,
  LockKeyhole,
  Mail,
  Sparkles,
  UserRound,
} from "lucide-react";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function OnboardingPage() {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    restaurant_name: "",
    full_name: "",
    email: "",
    password: "",
    confirm_password: "",
  });

  const [fieldErrors, setFieldErrors] = useState({});
  const [nonFieldErrors, setNonFieldErrors] = useState([]);
  const [loading, setLoading] = useState(false);

  function handleChange(event) {
    const { name, value } = event.target;

    setFormData((previous) => ({
      ...previous,
      [name]: value,
    }));

    setFieldErrors((previous) => ({
      ...previous,
      [name]: null,
    }));

    setNonFieldErrors([]);
  }

  function normalizeErrors(errorData) {
    const nextFieldErrors = {};
    const nextNonFieldErrors = [];

    if (!errorData) {
      nextNonFieldErrors.push("Something went wrong. Please try again.");
      return { nextFieldErrors, nextNonFieldErrors };
    }

    Object.entries(errorData).forEach(([key, value]) => {
      const messages = Array.isArray(value) ? value : [String(value)];

      if (key === "non_field_errors" || key === "__all__" || key === "detail") {
        nextNonFieldErrors.push(...messages);
      } else {
        nextFieldErrors[key] = messages;
      }
    });

    return { nextFieldErrors, nextNonFieldErrors };
  }

  async function handleSubmit(event) {
    event.preventDefault();

    if (formData.password !== formData.confirm_password) {
      setFieldErrors({
        confirm_password: ["Passwords do not match."],
      });
      return;
    }

    setLoading(true);
    setFieldErrors({});
    setNonFieldErrors([]);

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/restaurants/register/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(formData),
        }
      );

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        const { nextFieldErrors, nextNonFieldErrors } = normalizeErrors(data);

        setFieldErrors(nextFieldErrors);
        setNonFieldErrors(
          nextNonFieldErrors.length
            ? nextNonFieldErrors
            : ["Registration failed. Please review the form and try again."]
        );

        return;
      }

      if (data?.access) {
        localStorage.setItem("accessToken", data.access);
      }

      if (data?.refresh) {
        localStorage.setItem("refreshToken", data.refresh);
      }

      navigate("/dashboard");
    } catch (error) {
      console.error("Registration error:", error);

      setNonFieldErrors([
        "Unable to connect to the server. Please make sure the backend is running.",
      ]);
    } finally {
      setLoading(false);
    }
  }

  const inputClass =
    "w-full rounded-xl border border-slate-200 bg-white px-11 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-amber-500 focus:ring-4 focus:ring-amber-100";

  return (
    <div
      className="min-h-screen bg-slate-950 bg-cover bg-center"
      style={{
        backgroundImage: `url(${restaurantBackground})`,
      }}>
      <div className="min-h-screen bg-gradient-to-br from-slate-950/95 via-slate-950/85 to-amber-950/60">
        <div className="mx-auto grid min-h-screen max-w-7xl items-center gap-10 px-5 py-8 lg:grid-cols-2 lg:px-10">
          {/* Brand / marketing column */}
          <section className="hidden text-white lg:block">
            <div className="mb-10 inline-flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-400 font-black text-slate-950 shadow-lg shadow-amber-500/20">
                BE
              </div>

              <div>
                <div className="text-lg font-bold tracking-wide">BEEPOS</div>
                <div className="text-xs font-medium text-slate-300">
                  Smart Restaurant Management
                </div>
              </div>
            </div>

            <div className="max-w-xl">
              <div className="mb-5 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.24em] text-amber-300">
                <Sparkles size={15} />
                Built for modern restaurants
              </div>

              <h1 className="text-5xl font-black leading-tight tracking-tight xl:text-6xl">
                Run your restaurant with clarity and speed.
              </h1>

              <p className="mt-6 max-w-lg text-lg leading-8 text-slate-200">
                Create your restaurant workspace, manage products and orders,
                organize tables, and keep your team connected through one
                powerful POS platform.
              </p>

              <div className="mt-10 space-y-4 text-sm text-slate-100">
                <Feature text="Fast order management for dine-in and take-out" />
                <Feature text="Products, categories, modifiers, and inventory-ready setup" />
                <Feature text="Kitchen workflow, reports, tables, and pickup display" />
              </div>
            </div>

            <p className="mt-14 text-xs font-medium tracking-wide text-slate-400">
              © {new Date().getFullYear()} BEEPOS. Restaurant operations made
              simpler.
            </p>
          </section>

          {/* Registration card */}
          <section className="mx-auto w-full max-w-xl">
            <div className="rounded-3xl border border-white/50 bg-white/95 p-6 shadow-2xl backdrop-blur md:p-9">
              <div className="mb-7 text-center">
                <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-400 text-sm font-black text-slate-950 lg:hidden">
                  BE
                </div>

                <h2 className="text-2xl font-bold text-slate-900">
                  Set up your BEEPOS account
                </h2>

                <p className="mt-2 text-sm text-slate-500">
                  Create your restaurant and owner account in a few steps.
                </p>
              </div>

              {nonFieldErrors.length > 0 && (
                <ul className="mb-5 space-y-1 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {nonFieldErrors.map((error, index) => (
                    <li key={index}>{error}</li>
                  ))}
                </ul>
              )}

              <form
                onSubmit={handleSubmit}
                className="space-y-4">
                <FormField
                  id="restaurant_name"
                  name="restaurant_name"
                  label="Restaurant name"
                  value={formData.restaurant_name}
                  onChange={handleChange}
                  placeholder="Example: Bee Cafe"
                  icon={<Building2 size={18} />}
                  errors={fieldErrors.restaurant_name}
                  inputClass={inputClass}
                />

                <FormField
                  id="full_name"
                  name="full_name"
                  label="Your full name"
                  value={formData.full_name}
                  onChange={handleChange}
                  placeholder="Example: Jane Owner"
                  icon={<UserRound size={18} />}
                  errors={fieldErrors.full_name}
                  inputClass={inputClass}
                />

                <FormField
                  id="email"
                  name="email"
                  label="Email address"
                  type="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="owner@example.com"
                  icon={<Mail size={18} />}
                  errors={fieldErrors.email}
                  inputClass={inputClass}
                />

                <FormField
                  id="password"
                  name="password"
                  label="Password"
                  type="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="Minimum 8 characters"
                  icon={<LockKeyhole size={18} />}
                  errors={fieldErrors.password}
                  inputClass={inputClass}
                  minLength={8}
                />

                <FormField
                  id="confirm_password"
                  name="confirm_password"
                  label="Confirm password"
                  type="password"
                  value={formData.confirm_password}
                  onChange={handleChange}
                  placeholder="Repeat your password"
                  icon={<LockKeyhole size={18} />}
                  errors={fieldErrors.confirm_password}
                  inputClass={inputClass}
                  minLength={8}
                />

                <button
                  type="submit"
                  disabled={loading}
                  className="mt-2 w-full rounded-xl bg-amber-400 px-4 py-3.5 text-sm font-bold text-slate-950 shadow-lg shadow-amber-500/25 transition hover:bg-amber-300 disabled:cursor-not-allowed disabled:opacity-60">
                  {loading
                    ? "Creating your workspace..."
                    : "Create BEEPOS Account"}
                </button>
              </form>

              <div className="mt-6 text-center text-sm text-slate-600">
                Already have an account?{" "}
                <Link
                  to="/login"
                  className="font-bold text-amber-700 transition hover:text-amber-800">
                  Log in
                </Link>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

function Feature({ text }) {
  return (
    <div className="flex items-start gap-3">
      <CheckCircle2
        size={20}
        className="mt-0.5 shrink-0 text-amber-300"
      />
      <span>{text}</span>
    </div>
  );
}

function FormField({
  id,
  name,
  label,
  type = "text",
  value,
  onChange,
  placeholder,
  icon,
  errors,
  inputClass,
  minLength,
}) {
  return (
    <div>
      <label
        htmlFor={id}
        className="mb-1.5 block text-sm font-semibold text-slate-800">
        {label}
      </label>

      <div className="relative">
        <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
          {icon}
        </div>

        <input
          id={id}
          name={name}
          type={type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          minLength={minLength}
          required
          className={inputClass}
        />
      </div>

      {errors?.length > 0 && (
        <ul className="mt-1.5 list-disc pl-5 text-xs text-red-600">
          {errors.map((error, index) => (
            <li key={index}>{error}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default OnboardingPage;
