const ACTIVITIES = [
  {
    id: 1,
    user: "admin@beepos.com",
    action: "Updated product price",
    target: "Margherita Pizza",
    at: "2025-10-05 14:23",
  },
  {
    id: 2,
    user: "manager@beepos.com",
    action: "Added new staff user",
    target: "cashier@beepos.com",
    at: "2025-10-04 11:10",
  },
  {
    id: 3,
    user: "admin@beepos.com",
    action: "Changed restaurant settings",
    target: "Tax rate",
    at: "2025-10-03 09:45",
  },
  {
    id: 4,
    user: "system",
    action: "Daily backup completed",
    target: "-",
    at: "2025-10-03 02:00",
  },
];

export default function ActivityPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">Activity Log</h1>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-slate-700">
              <tr>
                <th className="text-left px-4 py-3 font-semibold">User</th>
                <th className="text-left px-4 py-3 font-semibold">Action</th>
                <th className="text-left px-4 py-3 font-semibold">Target</th>
                <th className="text-left px-4 py-3 font-semibold">Time</th>
              </tr>
            </thead>
            <tbody>
              {ACTIVITIES.map((row) => (
                <tr
                  key={row.id}
                  className="border-t border-slate-100">
                  <td className="px-4 py-3 text-slate-800">{row.user}</td>
                  <td className="px-4 py-3 text-slate-700">{row.action}</td>
                  <td className="px-4 py-3 text-slate-600">{row.target}</td>
                  <td className="px-4 py-3 text-slate-600">{row.at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
