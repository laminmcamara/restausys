import { useState } from "react";

const INITIAL_KEYS = [
  {
    id: 1,
    name: "Production Key",
    key: "pk_live_••••••••••••1234",
    createdAt: "2025-07-10",
  },
  {
    id: 2,
    name: "Test Key",
    key: "pk_test_••••••••••••5678",
    createdAt: "2025-08-01",
  },
];

export default function DevelopersPage() {
  const [keys, setKeys] = useState(INITIAL_KEYS);
  const [newKeyName, setNewKeyName] = useState("");

  function handleCreateKey(e) {
    e.preventDefault();
    if (!newKeyName.trim()) return;

    const newKey = {
      id: Date.now(),
      name: newKeyName,
      key: `pk_${
        Math.random() > 0.5 ? "live" : "test"
      }_••••••••••••${Math.floor(Math.random() * 9000 + 1000)}`,
      createdAt: new Date().toISOString().slice(0, 10),
    };

    setKeys((k) => [newKey, ...k]);
    setNewKeyName("");
  }

  function handleRevoke(id) {
    if (!confirm("Revoke this API key? This action cannot be undone.")) return;
    setKeys((k) => k.filter((key) => key.id !== id));
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">API & Developers</h1>

      {/* Docs links */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-semibold text-slate-800 mb-3">
          Documentation
        </h2>
        <ul className="list-disc pl-5 text-slate-700 space-y-1">
          <li>
            <a
              href="/api-docs"
              target="_blank"
              rel="noopener noreferrer"
              className="text-amber-700 hover:text-amber-800 font-medium">
              REST API Reference
            </a>
          </li>
          <li>
            <a
              href="/webhooks-docs"
              target="_blank"
              rel="noopener noreferrer"
              className="text-amber-700 hover:text-amber-800 font-medium">
              Webhooks Guide
            </a>
          </li>
          <li>
            <a
              href="/integration-examples"
              target="_blank"
              rel="noopener noreferrer"
              className="text-amber-700 hover:text-amber-800 font-medium">
              Integration Examples
            </a>
          </li>
        </ul>
      </div>

      {/* Create key */}
      <form
        onSubmit={handleCreateKey}
        className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-semibold text-slate-800 mb-4">
          Create API Key
        </h2>
        <div className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            placeholder="Key name (e.g. 'Production')"
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
          />
          <button
            type="submit"
            className="bg-amber-400 hover:bg-amber-500 text-slate-950 font-semibold px-4 py-2 rounded-lg text-sm transition">
            Create Key
          </button>
        </div>
      </form>

      {/* Keys list */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-slate-700">
              <tr>
                <th className="text-left px-4 py-3 font-semibold">Name</th>
                <th className="text-left px-4 py-3 font-semibold">Key</th>
                <th className="text-left px-4 py-3 font-semibold">Created</th>
                <th className="text-right px-4 py-3 font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {keys.map((key) => (
                <tr
                  key={key.id}
                  className="border-t border-slate-100">
                  <td className="px-4 py-3 text-slate-800">{key.name}</td>
                  <td className="px-4 py-3 text-slate-600 font-mono">
                    {key.key}
                  </td>
                  <td className="px-4 py-3 text-slate-600">{key.createdAt}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      type="button"
                      onClick={() => handleRevoke(key.id)}
                      className="text-red-600 hover:text-red-700 font-medium">
                      Revoke
                    </button>
                  </td>
                </tr>
              ))}
              {keys.length === 0 && (
                <tr>
                  <td
                    colSpan={4}
                    className="px-4 py-6 text-center text-slate-500">
                    No API keys configured.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
