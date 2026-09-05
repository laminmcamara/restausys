import { NavLink } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { useTranslation } from "react-i18next";
import {
  User,
  BookOpen,
  HelpCircle,
  KeyRound,
  CreditCard,
  Activity,
  Monitor,
  ShieldCheck,
  ExternalLink,
} from "lucide-react";

export default function RightSidebar() {
  const { user } = useAuth();
  const { t } = useTranslation();

  const userName = user?.email || user?.username || "User";
  const restaurantName = user?.restaurant?.name || "Restaurant";

  // Check for admin status in your CustomUser model
  const isStaffOrAdmin = user?.is_staff || user?.is_superuser;

  return (
    <aside className="w-64 bg-white border-l border-slate-200 p-4 space-y-4 overflow-y-auto h-full">
      {/* Profile Card */}
      <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-full bg-amber-400 text-slate-950 flex items-center justify-center font-black text-sm">
            {userName.charAt(0).toUpperCase()}
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-800 truncate w-32">
              {userName}
            </div>
            <div className="text-xs text-slate-500 truncate w-32">
              {restaurantName}
            </div>
          </div>
        </div>

        <NavLink
          to="/dashboard/settings/profile"
          className="mt-3 inline-flex items-center space-x-2 text-xs font-medium text-amber-700 hover:text-amber-800">
          <User size={24} />
          <span>{t("profile.viewProfile")}</span>
        </NavLink>
      </div>

      {/* Quick Links (Your Original Links) */}
      <div className="space-y-2">
        <NavLink
          to="/dashboard/tutorials"
          className="flex items-center space-x-3 px-3 py-2 rounded-lg hover:bg-slate-50 text-slate-700">
          <BookOpen size={24} />
          <span className="text-sm font-medium">{t("profile.tutorials")}</span>
        </NavLink>

        <NavLink
          to="/dashboard/help"
          className="flex items-center space-x-3 px-3 py-2 rounded-lg hover:bg-slate-50 text-slate-700">
          <HelpCircle size={24} />
          <span className="text-sm font-medium">{t("profile.help")}</span>
        </NavLink>

        <NavLink
          to="/dashboard/developers"
          className="flex items-center space-x-3 px-3 py-2 rounded-lg hover:bg-slate-50 text-slate-700">
          <KeyRound size={24} />
          <span className="text-sm font-medium">{t("profile.apiKeys")}</span>
        </NavLink>

        <NavLink
          to="/dashboard/billing"
          className="flex items-center space-x-3 px-3 py-2 rounded-lg hover:bg-slate-50 text-slate-700">
          <CreditCard size={24} />
          <span className="text-sm font-medium">{t("profile.billing")}</span>
        </NavLink>

        <NavLink
          to="/dashboard/activity"
          className="flex items-center space-x-3 px-3 py-2 rounded-lg hover:bg-slate-50 text-slate-700">
          <Activity size={24} />
          <span className="text-sm font-medium">{t("profile.activity")}</span>
        </NavLink>

        {/* NEW: Pickup Display Link */}
        <NavLink
          to="/pickup"
          target="_blank"
          className="flex items-center space-x-3 px-3 py-2 rounded-lg bg-indigo-50 text-indigo-700 hover:bg-indigo-100 transition-colors">
          <Monitor size={24} />
          <span className="text-sm font-bold">Pickup Display</span>
        </NavLink>
      </div>

      {/* NEW: Admin Section (Visible to SuperUsers/Staff) */}
      {isStaffOrAdmin && (
        <div className="pt-4 border-t border-slate-100">
          <a
            href="http://localhost:8000/admin/"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-between px-3 py-2 rounded-lg bg-rose-50 text-rose-700 hover:bg-rose-100 transition-colors">
            <div className="flex items-center space-x-3">
              <ShieldCheck size={24} />
              <span className="text-sm font-bold">Django Admin</span>
            </div>
            <ExternalLink size={14} />
          </a>
        </div>
      )}
    </aside>
  );
}
