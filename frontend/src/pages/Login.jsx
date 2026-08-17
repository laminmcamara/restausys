import React, { useState } from "react";
import { useAuth } from "../hooks/useAuth";
import { Link, useNavigate } from "react-router-dom";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    const success = await login(username, password);

    setLoading(false);

    if (success) {
      navigate("/dashboard", { replace: true });
    } else {
      setError("Invalid username or password.");
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex justify-center md:justify-end md:pr-24">
      <div className="w-full md:w-1/3 min-h-screen overflow-y-auto bg-white shadow-2xl px-8 py-10 md:px-10">
        <div className="min-h-full flex flex-col justify-center">
          <div className="mb-10">
            <p className="text-sm font-bold uppercase tracking-wide text-blue-600">
              Welcome back
            </p>

            <h2 className="mt-3 text-4xl font-black text-slate-950">Login</h2>

            <p className="mt-3 text-base text-slate-500">
              Sign in to access your restaurant dashboard.
            </p>
          </div>

          {error && (
            <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
              {error}
            </div>
          )}

          <form
            onSubmit={handleSubmit}
            className="space-y-5">
            <div>
              <label className="mb-2 block text-sm font-bold text-slate-700">
                Username
              </label>

              <input
                type="text"
                placeholder="Enter your username"
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-4 text-base font-medium text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-600 focus:ring-4 focus:ring-blue-100"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                required
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-bold text-slate-700">
                Password
              </label>

              <input
                type="password"
                placeholder="Enter your password"
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-4 text-base font-medium text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-600 focus:ring-4 focus:ring-blue-100"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl bg-blue-600 px-6 py-4 text-lg font-extrabold text-white shadow-lg transition hover:bg-blue-700 hover:scale-105 active:scale-95 disabled:cursor-not-allowed disabled:opacity-70 disabled:hover:scale-100">
              {loading ? "Logging in..." : "Login"}
            </button>
          </form>

          <div className="mt-8 border-t border-slate-200 pt-8 text-center">
            <p className="text-sm font-medium text-slate-600">
              Don&apos;t have an account?
            </p>

            <Link
              to="/onboarding"
              className="mt-3 inline-flex items-center justify-center rounded-xl border border-blue-600 px-6 py-3 text-base font-extrabold text-blue-600 transition hover:bg-blue-50">
              Create Account
            </Link>
          </div>

          <div className="mt-8 rounded-2xl bg-slate-50 p-5">
            <p className="text-sm font-semibold text-slate-600">
              Secure access for managers, cashiers, servers, cooks, and staff.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
