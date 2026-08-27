import React, { useState, useEffect } from "react";
import api from "../services/api"; // Import your axios instance
import {
  Shield,
  TestTube,
  Save,
  RefreshCw,
  Copy,
  Check,
  Book,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

export default function DevelopersPage() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [copiedKey, setCopiedKey] = useState(null);
  const [openDoc, setOpenDoc] = useState(null);

  useEffect(() => {
    // Axios automatically includes the token via your interceptor
    api
      .get("/developer/webhook-config/")
      .then((res) => {
        setConfig(res.data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load config", err);
        setLoading(false);
      });
  }, []);

  const handleSave = async () => {
    try {
      await api.post("/developer/webhook-config/", config);
      alert("Settings Saved Successfully!");
    } catch (err) {
      alert("Failed to save settings.");
    }
  };

  const handleRegenerate = async (keyType) => {
    if (
      !confirm("Warning: The old key will stop working immediately. Continue?")
    )
      return;
    try {
      const res = await api.post("/developer/regenerate-key/", {
        type: keyType,
      });
      setConfig({ ...config, [keyType]: res.data.new_value });
    } catch (err) {
      alert("Failed to regenerate key.");
    }
  };

  const copy = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(id);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  if (loading)
    return (
      <div className="p-10 text-center text-slate-500">
        Loading Developer Portal...
      </div>
    );
  if (!config)
    return (
      <div className="p-10 text-center text-red-500">
        Error loading configuration.
      </div>
    );

  return (
    <div className="max-w-6xl mx-auto p-8 space-y-8 bg-slate-50 min-h-screen">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">
            Developer Portal
          </h1>
          <p className="text-slate-500 mt-2">
            Integrate your third-party applications with BEEPOS.
          </p>
        </div>
        <button
          onClick={handleSave}
          className="flex items-center gap-2 bg-slate-900 text-white px-6 py-2.5 rounded-xl font-bold hover:bg-slate-800 transition shadow-sm">
          <Save className="w-4 h-4" /> Save Changes
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <KeyCard
          title="Sandbox Environment"
          icon={<TestTube className="text-amber-600" />}
          colorClass="amber"
          config={config}
          setConfig={setConfig}
          isLive={false}
          onRegen={handleRegenerate}
          onCopy={copy}
          copiedKey={copiedKey}
        />
        <KeyCard
          title="Production Environment"
          icon={<Shield className="text-emerald-600" />}
          colorClass="emerald"
          config={config}
          setConfig={setConfig}
          isLive={true}
          onRegen={handleRegenerate}
          onCopy={copy}
          copiedKey={copiedKey}
        />
      </div>

      <div className="mt-12 space-y-4">
        <div className="flex items-center gap-2 text-slate-800 font-bold text-lg mb-4">
          <Book className="w-5 h-5" /> Quick Start Documentation
        </div>
        <DocAccordion
          title="How to Authenticate (Inbound API)"
          isOpen={openDoc === 1}
          onClick={() => setOpenDoc(openDoc === 1 ? null : 1)}>
          <p className="mb-2">
            Include your API key in the request header for all API calls:
          </p>
          <div className="bg-slate-900 text-slate-300 p-4 rounded-lg font-mono text-sm">
            GET /api/v1/orders/ <br />
            Authorization: Bearer{" "}
            <span className="text-emerald-400">your_api_key_here</span>
          </div>
        </DocAccordion>
      </div>
    </div>
  );
}

const KeyCard = ({
  title,
  icon,
  colorClass,
  config,
  setConfig,
  isLive,
  onRegen,
  onCopy,
  copiedKey,
}) => {
  const prefix = isLive ? "live" : "test";
  const isEnabled = config[`is_${prefix}_enabled`];

  return (
    <div
      className={`bg-white rounded-2xl border border-${colorClass}-200 shadow-sm overflow-hidden`}>
      <div
        className={`bg-${colorClass}-50 px-6 py-4 border-b border-${colorClass}-200 flex justify-between items-center`}>
        <div className="flex items-center gap-2 font-bold text-slate-800">
          {icon} {title}
        </div>
        <label className="flex items-center gap-2 cursor-pointer">
          <span className="text-xs font-medium text-slate-500">
            {isEnabled ? "Enabled" : "Disabled"}
          </span>
          <input
            type="checkbox"
            checked={isEnabled}
            onChange={(e) =>
              setConfig({
                ...config,
                [`is_${prefix}_enabled`]: e.target.checked,
              })
            }
            className="w-4 h-4 accent-slate-900"
          />
        </label>
      </div>
      <div className="p-6 space-y-5">
        <Field
          label="API Key"
          value={config[`${prefix}_api_key`]}
          onRegen={() => onRegen(`${prefix}_api_key`)}
          onCopy={() => onCopy(config[`${prefix}_api_key`], `${prefix}_k`)}
          copied={copiedKey === `${prefix}_k`}
        />
        <Field
          label="Signing Secret"
          value={config[`${prefix}_secret`]}
          onRegen={() => onRegen(`${prefix}_secret`)}
          onCopy={() => onCopy(config[`${prefix}_secret`], `${prefix}_s`)}
          copied={copiedKey === `${prefix}_s`}
        />
        <div className="space-y-1">
          <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">
            Webhook Destination URL
          </label>
          <input
            type="url"
            value={config[`${prefix}_webhook_url`] || ""}
            onChange={(e) =>
              setConfig({
                ...config,
                [`${prefix}_webhook_url`]: e.target.value,
              })
            }
            placeholder="https://your-server.com/webhook"
            className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-slate-900 outline-none transition"
          />
        </div>
      </div>
    </div>
  );
};

const Field = ({ label, value, onRegen, onCopy, copied }) => (
  <div className="space-y-1">
    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">
      {label}
    </label>
    <div className="flex gap-2">
      <div className="flex-1 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 font-mono text-xs truncate text-slate-600 self-center">
        {value}
      </div>
      <button
        onClick={onCopy}
        className="p-2 hover:bg-slate-100 rounded-lg border border-slate-200 transition">
        {copied ? (
          <Check className="w-4 h-4 text-emerald-600" />
        ) : (
          <Copy className="w-4 h-4 text-slate-500" />
        )}
      </button>
      <button
        onClick={onRegen}
        className="p-2 hover:bg-red-50 rounded-lg border border-transparent hover:border-red-100 transition text-red-400 hover:text-red-600">
        <RefreshCw className="w-4 h-4" />
      </button>
    </div>
  </div>
);

const DocAccordion = ({ title, children, isOpen, onClick }) => (
  <div className="border border-slate-200 rounded-xl bg-white overflow-hidden shadow-sm">
    <button
      onClick={onClick}
      className="w-full px-6 py-4 flex justify-between items-center hover:bg-slate-50 transition">
      <span className="font-semibold text-slate-700">{title}</span>
      {isOpen ? (
        <ChevronUp className="w-4 h-4 text-slate-400" />
      ) : (
        <ChevronDown className="w-4 h-4 text-slate-400" />
      )}
    </button>
    {isOpen && (
      <div className="px-6 py-4 border-t border-slate-100 text-sm text-slate-600 bg-slate-50/50">
        {children}
      </div>
    )}
  </div>
);
