import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Folder, Settings, KeyRound, LifeBuoy, FileText } from "lucide-react";

export default function DashboardFooter() {
  const { t } = useTranslation();

  return (
    <footer className="mt-6 border-t border-slate-200 pt-6 text-sm">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        <div>
          <h4 className="font-semibold text-slate-800 mb-2">
            {t("footer.system")}
          </h4>
          <ul className="space-y-1">
            <li>
              <NavLink
                to="/dashboard/files"
                className="flex items-center space-x-2 text-slate-600 hover:text-amber-700">
                <Folder size={24} />
                <span>{t("footer.fileManagement")}</span>
              </NavLink>
            </li>
            <li>
              <NavLink
                to="/dashboard/settings"
                className="flex items-center space-x-2 text-slate-600 hover:text-amber-700">
                <Settings size={24} />
                <span>{t("footer.settings")}</span>
              </NavLink>
            </li>
          </ul>
        </div>

        <div>
          <h4 className="font-semibold text-slate-800 mb-2">
            {t("footer.developers")}
          </h4>
          <ul className="space-y-1">
            <li>
              <NavLink
                to="/dashboard/developers"
                className="flex items-center space-x-2 text-slate-600 hover:text-amber-700">
                <KeyRound size={24} />
                <span>{t("footer.apiDocs")}</span>
              </NavLink>
            </li>
          </ul>
        </div>

        <div>
          <h4 className="font-semibold text-slate-800 mb-2">
            {t("footer.support")}
          </h4>
          <ul className="space-y-1">
            <li>
              <NavLink
                to="/dashboard/help"
                className="flex items-center space-x-2 text-slate-600 hover:text-amber-700">
                <LifeBuoy size={24} />
                <span>{t("footer.contactSupport")}</span>
              </NavLink>
            </li>
          </ul>
        </div>

        <div>
          <h4 className="font-semibold text-slate-800 mb-2">
            {t("footer.legal")}
          </h4>
          <ul className="space-y-1">
            <li>
              <NavLink
                to="/dashboard/privacy"
                className="flex items-center space-x-2 text-slate-600 hover:text-amber-700">
                <FileText size={16} />
                <span>{t("footer.privacy")}</span>
              </NavLink>
            </li>
            <li>
              <NavLink
                to="/dashboard/terms"
                className="flex items-center space-x-2 text-slate-600 hover:text-amber-700">
                <FileText size={16} />
                <span>{t("footer.terms")}</span>
              </NavLink>
            </li>
          </ul>
        </div>
      </div>

      <div className="mt-6 text-xs text-slate-500">
        © {new Date().getFullYear()} BEEPOS. All rights reserved.
      </div>
    </footer>
  );
}
