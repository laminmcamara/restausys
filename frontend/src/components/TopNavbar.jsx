import React, { useState } from "react";
import { Link } from "react-router-dom";
import LanguageSwitcher from "./LanguageSwitcher";

export default function TopNavbar() {
  const [restaurantOpen, setRestaurantOpen] = useState(false);

  return (
    <header className="border-b border-slate-200 bg-white px-6 py-4 shadow-sm">
      <nav className="flex items-center justify-between gap-6">
        {/* Left side: logo + restaurant menu */}
        <div className="flex items-center gap-6">
          <Link
            to="/dashboard"
            className="text-lg font-black text-slate-900">
            POS Dashboard
          </Link>

          <div className="relative">
            <button
              type="button"
              onClick={() => setRestaurantOpen((prev) => !prev)}
              className="rounded-xl px-4 py-2 text-sm font-bold text-slate-700 transition hover:bg-slate-100">
              Restaurant
            </button>

            {restaurantOpen && (
              <div className="absolute left-0 top-12 z-50 w-48 rounded-2xl border border-slate-200 bg-white p-2 shadow-xl">
                <Link
                  to="/dashboard/restaurant/dine-in"
                  onClick={() => setRestaurantOpen(false)}
                  className="block rounded-xl px-4 py-3 text-sm font-bold text-slate-700 hover:bg-blue-50 hover:text-blue-700">
                  Dine-in
                </Link>

                <Link
                  to="/dashboard/restaurant/take-out"
                  onClick={() => setRestaurantOpen(false)}
                  className="block rounded-xl px-4 py-3 text-sm font-bold text-slate-700 hover:bg-blue-50 hover:text-blue-700">
                  Take-out
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* Right side: language + (future) profile */}
        <div className="flex items-center gap-4">
          <LanguageSwitcher />

          {/* Placeholder for future profile/email dropdown */}
          {/* <ProfileMenu /> */}
        </div>
      </nav>
    </header>
  );
}
