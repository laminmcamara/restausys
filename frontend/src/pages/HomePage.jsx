import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
// import { Link } from "react-router-dom";
import {
  ArrowRight,
  BarChart3,
  CheckCircle2,
  ChefHat,
  CircleDollarSign,
  Clock3,
  LayoutDashboard,
  LockKeyhole,
  Mail,
  MenuSquare,
  Monitor,
  ShieldCheck,
  UtensilsCrossed,
} from "lucide-react";
import logo from "../assets/logo.png";
import restaurantBackground from "../assets/beepos-restaurant-bg.jpg";

export default function HomePage() {
  const token =
    localStorage.getItem("access") ||
    localStorage.getItem("accessToken") ||
    localStorage.getItem("token");
  const navigate = useNavigate();

  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState("");

  const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

  async function handleLogin(event) {
    event.preventDefault();
    setLoginLoading(true);
    setLoginError("");

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/token/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: loginEmail,
          password: loginPassword,
        }),
      });

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        setLoginError(
          data?.detail || "Invalid email or password. Please try again."
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
      setLoginError("Unable to connect to the server. Is the backend running?");
    } finally {
      setLoginLoading(false);
    }
  }

  const primaryPath = token ? "/dashboard" : "/login";
  const primaryText = token ? "Open Dashboard" : "Log In";

  return (
    <div className="min-h-screen overflow-x-hidden bg-slate-950 text-white">
      {/* Hero background */}
      <section
        className="relative isolate min-h-[760px] bg-cover bg-center"
        style={{
          backgroundImage: `url(${restaurantBackground})`,
        }}>
        <div className="absolute inset-0 -z-10 bg-slate-950/50" />
        <div className="absolute inset-0 -z-10 bg-gradient-to-br from-slate-950/70 via-slate-950/50 to-amber-950/30" />
        <div className="absolute inset-x-0 bottom-0 -z-10 h-72 bg-gradient-to-t from-slate-950 to-transparent" />

        {/* Navbar */}
        <header className="border-b border-white/10 bg-slate-950/20 backdrop-blur-sm">
          <nav className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 md:px-8">
            <Link
              to="/"
              className="flex items-center gap-3">
              <img
                src={logo}
                alt="BEEPOS logo"
                className="h-12 w-12 rounded-xl object-contain shadow-lg"
              />

              <div>
                <h1 className="text-xl font-black tracking-tight text-amber-300">
                  BEEPOS
                </h1>
                <p className="text-xs font-medium text-slate-300">
                  Smart Restaurant Management
                </p>
              </div>
            </Link>

            <div className="flex items-center gap-2 sm:gap-4">
              {!token && (
                <Link
                  to="/onboarding"
                  className="hidden text-sm font-semibold text-slate-200 transition hover:text-amber-300 sm:block">
                  Create account
                </Link>
              )}

              <Link
                to={primaryPath}
                className="inline-flex items-center gap-2 rounded-xl bg-amber-400 px-4 py-2.5 text-sm font-black text-slate-950 shadow-lg shadow-amber-500/20 transition hover:bg-amber-300 sm:px-5">
                {primaryText}
                <ArrowRight size={16} />
              </Link>
            </div>
          </nav>
        </header>

        {/* Main hero */}
        <div className="mx-auto grid max-w-7xl gap-12 px-5 py-16 md:px-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-center lg:py-24">
          <div className="max-w-3xl">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-amber-300/30 bg-amber-400/10 px-4 py-2 text-xs font-bold uppercase tracking-[0.16em] text-amber-200">
              <SparkIcon />
              Effective restaurant work starts with BEEPOS
            </div>

            <h2 className="max-w-3xl text-5xl font-black leading-[1.02] tracking-tight text-white sm:text-6xl lg:text-7xl">
              Automate your
              <span className="block text-amber-300">restaurant.</span>
            </h2>

            <p className="mt-7 max-w-2xl text-base leading-8 text-slate-200 sm:text-lg">
              BEEPOS brings orders, menus, tables, kitchen workflow, payments,
              and reporting together in one simple workspace—so your team can
              serve customers faster and manage operations with confidence.
            </p>

            <div className="mt-8 flex flex-wrap gap-4">
              <Link
                to={primaryPath}
                className="inline-flex items-center gap-2 rounded-2xl bg-amber-400 px-6 py-4 text-sm font-black text-slate-950 shadow-xl shadow-amber-500/25 transition hover:bg-amber-300">
                {token ? "Go to BEEPOS Dashboard" : "Get Started"}
                <ArrowRight size={18} />
              </Link>

              {!token && (
                <Link
                  to="/onboarding"
                  className="rounded-2xl border border-white/25 bg-white/5 px-6 py-4 text-sm font-bold text-white backdrop-blur-sm transition hover:bg-white/10">
                  Register your restaurant
                </Link>
              )}
            </div>

            <div className="mt-11 grid max-w-2xl gap-3 sm:grid-cols-3">
              <HeroStat
                icon={<Clock3 size={18} />}
                value="Fast"
                label="Order taking"
              />
              <HeroStat
                icon={<ChefHat size={18} />}
                value="Live"
                label="Kitchen workflow"
              />
              <HeroStat
                icon={<ShieldCheck size={18} />}
                value="Simple"
                label="Menu management"
              />
            </div>
          </div>

          {/* Login card or dashboard preview */}
          <div className="relative mx-auto w-full max-w-lg lg:max-w-none">
            <div className="absolute -inset-4 rounded-[2rem] bg-amber-400/15 blur-3xl" />

            <div className="relative overflow-hidden rounded-[2rem] border border-white/20 bg-white/95 p-6 shadow-2xl shadow-black/40 backdrop-blur sm:p-8">
              {token ? (
                <>
                  <div className="mb-6 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-amber-400 text-sm font-black text-slate-950">
                        BE
                      </div>
                      <div>
                        <p className="font-black text-slate-900">BEEPOS</p>
                        <p className="text-xs text-slate-500">
                          Restaurant control center
                        </p>
                      </div>
                    </div>
                    <div className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-700">
                      System online
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <DashboardTile
                      icon={<UtensilsCrossed size={20} />}
                      title="Menu"
                      text="Products & modifiers"
                      color="bg-amber-100 text-amber-800"
                    />
                    <DashboardTile
                      icon={<LayoutDashboard size={20} />}
                      title="Orders"
                      text="Dine-in & take-out"
                      color="bg-blue-100 text-blue-800"
                    />
                    <DashboardTile
                      icon={<ChefHat size={20} />}
                      title="Kitchen"
                      text="Live order queue"
                      color="bg-orange-100 text-orange-800"
                    />
                    <DashboardTile
                      icon={<BarChart3 size={20} />}
                      title="Reports"
                      text="Business insight"
                      color="bg-violet-100 text-violet-800"
                    />
                  </div>

                  <Link
                    to="/dashboard"
                    className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-amber-400 px-4 py-3.5 text-sm font-black text-slate-950 shadow-lg shadow-amber-500/25 transition hover:bg-amber-300">
                    Go to Dashboard
                    <ArrowRight size={18} />
                  </Link>
                </>
              ) : (
                <>
                  {/* Login form */}
                  <div className="mb-7 text-center">
                    <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-400 text-sm font-black text-slate-950">
                      BE
                    </div>
                    <h3 className="text-2xl font-black text-slate-900">
                      Welcome to BEEPOS
                    </h3>
                    <p className="mt-1.5 text-sm text-slate-500">
                      Log in to your restaurant workspace
                    </p>
                  </div>

                  {loginError && (
                    <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
                      {loginError}
                    </div>
                  )}

                  <form
                    onSubmit={handleLogin}
                    className="space-y-4">
                    <div>
                      <label
                        htmlFor="login-email"
                        className="mb-1.5 block text-sm font-semibold text-slate-800">
                        Email
                      </label>
                      <div className="relative">
                        <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
                          <Mail size={18} />
                        </div>
                        <input
                          id="login-email"
                          type="email"
                          required
                          value={loginEmail}
                          onChange={(e) => setLoginEmail(e.target.value)}
                          placeholder="owner@example.com"
                          className="w-full rounded-xl border border-slate-200 bg-white px-11 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-amber-500 focus:ring-4 focus:ring-amber-100"
                        />
                      </div>
                    </div>

                    <div>
                      <label
                        htmlFor="login-password"
                        className="mb-1.5 block text-sm font-semibold text-slate-800">
                        Password
                      </label>
                      <div className="relative">
                        <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
                          <LockKeyhole size={18} />
                        </div>
                        <input
                          id="login-password"
                          type="password"
                          required
                          value={loginPassword}
                          onChange={(e) => setLoginPassword(e.target.value)}
                          placeholder="Your password"
                          className="w-full rounded-xl border border-slate-200 bg-white px-11 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-amber-500 focus:ring-4 focus:ring-amber-100"
                        />
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-sm">
                      <label className="flex cursor-pointer items-center gap-2 text-slate-600">
                        <input
                          type="checkbox"
                          checked={rememberMe}
                          onChange={(e) => setRememberMe(e.target.checked)}
                          className="h-4 w-4 rounded border-slate-300 text-amber-500 focus:ring-amber-400"
                        />
                        Remember me
                      </label>
                      <Link
                        to="/login"
                        className="font-semibold text-amber-700 transition hover:text-amber-800">
                        Forgot password?
                      </Link>
                    </div>

                    <button
                      type="submit"
                      disabled={loginLoading}
                      className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl bg-amber-400 px-4 py-3.5 text-sm font-black text-slate-950 shadow-lg shadow-amber-500/25 transition hover:bg-amber-300 disabled:cursor-not-allowed disabled:opacity-60">
                      {loginLoading ? "Logging in..." : "Log In"}
                      {!loginLoading && <ArrowRight size={18} />}
                    </button>
                  </form>

                  <p className="mt-6 text-center text-sm text-slate-600">
                    Don't have an account?{" "}
                    <Link
                      to="/onboarding"
                      className="font-bold text-amber-700 transition hover:text-amber-800">
                      Sign up
                    </Link>
                  </p>
                </>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Feature section */}
      <main>
        <section className="bg-slate-950 px-5 py-20 md:px-8">
          <div className="mx-auto max-w-7xl">
            <div className="max-w-2xl">
              <p className="text-sm font-black uppercase tracking-[0.16em] text-amber-300">
                One connected platform
              </p>

              <h2 className="mt-4 text-3xl font-black tracking-tight text-white sm:text-4xl">
                Everything your restaurant needs to operate smoothly.
              </h2>

              <p className="mt-4 leading-7 text-slate-400">
                Use BEEPOS to streamline the daily tasks that matter most, while
                keeping orders, team workflows, and operational data in one
                place.
              </p>
            </div>

            <div className="mt-12 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
              <FeatureCard
                icon={<LayoutDashboard size={23} />}
                title="POS Dashboard"
                description="Create dine-in and take-out orders, manage tables, and keep service moving."
              />
              <FeatureCard
                icon={<ChefHat size={23} />}
                title="Kitchen Display"
                description="Send orders to the kitchen and give staff a clear live preparation queue."
              />
              <FeatureCard
                icon={<MenuSquare size={23} />}
                title="Menu Control"
                description="Organize categories, products, pricing, availability, and modifier groups."
              />
              <FeatureCard
                icon={<CircleDollarSign size={23} />}
                title="Payments"
                description="Track bills, mark paid orders, and maintain a clearer payment workflow."
              />
              <FeatureCard
                icon={<BarChart3 size={23} />}
                title="Reports"
                description="Review sales and business activity to make better daily operating decisions."
              />
              <FeatureCard
                icon={<Monitor size={23} />}
                title="Pickup Display"
                description="Keep customers informed with an accessible order pickup display screen."
              />
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="border-y border-amber-400/20 bg-gradient-to-r from-amber-400 via-yellow-300 to-amber-400 px-5 py-14 text-slate-950 md:px-8">
          <div className="mx-auto flex max-w-7xl flex-col gap-7 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-sm font-black uppercase tracking-[0.16em] text-slate-800">
                Ready to get started?
              </p>
              <h2 className="mt-2 text-3xl font-black tracking-tight">
                Build your restaurant workspace with BEEPOS.
              </h2>
            </div>

            <Link
              to={token ? "/dashboard" : "/onboarding"}
              className="inline-flex w-fit items-center gap-2 rounded-2xl bg-slate-950 px-6 py-4 text-sm font-black text-white shadow-lg transition hover:bg-slate-800">
              {token ? "Open Dashboard" : "Create an Account"}
              <ArrowRight size={18} />
            </Link>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="bg-slate-950 px-5 py-8 text-sm text-slate-400 md:px-8">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <p>© {new Date().getFullYear()} BEEPOS. All rights reserved.</p>

          <div className="flex flex-wrap gap-5">
            <Link
              to="/login"
              className="transition hover:text-amber-300">
              Log in
            </Link>
            <Link
              to="/onboarding"
              className="transition hover:text-amber-300">
              Register
            </Link>
            {token && (
              <Link
                to="/dashboard"
                className="transition hover:text-amber-300">
                Dashboard
              </Link>
            )}
          </div>
        </div>
      </footer>
    </div>
  );
}

function HeroStat({ icon, value, label }) {
  return (
    <div className="rounded-2xl border border-white/15 bg-slate-950/45 p-4 backdrop-blur-sm">
      <div className="mb-3 text-amber-300">{icon}</div>
      <p className="text-lg font-black text-white">{value}</p>
      <p className="mt-0.5 text-xs text-slate-300">{label}</p>
    </div>
  );
}

function DashboardTile({ icon, title, text, color }) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
      <div
        className={`mb-4 flex h-10 w-10 items-center justify-center rounded-xl ${color}`}>
        {icon}
      </div>
      <p className="font-bold text-slate-900">{title}</p>
      <p className="mt-1 text-xs text-slate-500">{text}</p>
    </div>
  );
}

function MiniMetric({ value, label }) {
  return (
    <div className="rounded-xl bg-white/10 px-3 py-2.5">
      <p className="font-black text-amber-300">{value}</p>
      <p className="mt-0.5 text-[11px] text-slate-300">{label}</p>
    </div>
  );
}

function FeatureCard({ icon, title, description }) {
  return (
    <article className="rounded-3xl border border-slate-800 bg-slate-900/70 p-7 transition duration-200 hover:-translate-y-1 hover:border-amber-400/50 hover:bg-slate-900">
      <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-400 text-slate-950">
        {icon}
      </div>

      <h3 className="text-xl font-black text-white">{title}</h3>
      <p className="mt-3 leading-7 text-slate-400">{description}</p>
    </article>
  );
}

function SparkIcon() {
  return <span className="text-base leading-none">✦</span>;
}
