import { useState } from "react";

const FAQS = [
  {
    q: "How do I reset my password?",
    a: "Go to Settings → Profile → Change Password, or use the 'Forgot password' link on the login page.",
  },
  {
    q: "Can I have multiple users for my restaurant?",
    a: "Yes. Go to Control Panel → Staff to add team members and assign roles.",
  },
  {
    q: "How do I export sales reports?",
    a: "Open Reports, choose date range, then click Export → CSV/Excel.",
  },
];

export default function HelpPage() {
  const [openIndex, setOpenIndex] = useState(null);
  const [form, setForm] = useState({ subject: "", message: "" });

  function handleChange(e) {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));
  }

  function handleSubmit(e) {
    e.preventDefault();
    // TODO: send to Django support endpoint
    alert("Support request sent (mock)");
    setForm({ subject: "", message: "" });
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">Help & Support</h1>

      {/* FAQs */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-semibold text-slate-800 mb-4">
          Frequently Asked Questions
        </h2>
        <div className="space-y-3">
          {FAQS.map((item, idx) => {
            const open = openIndex === idx;
            return (
              <div
                key={idx}
                className="border border-slate-200 rounded-lg">
                <button
                  type="button"
                  onClick={() => setOpenIndex(open ? null : idx)}
                  className="w-full flex items-center justify-between px-4 py-3 text-left">
                  <span className="font-medium text-slate-800">{item.q}</span>
                  <span className="text-slate-500">{open ? "−" : "+"}</span>
                </button>
                {open && (
                  <div className="px-4 pb-4 text-sm text-slate-600">
                    {item.a}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Contact form */}
      <form
        onSubmit={handleSubmit}
        className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-semibold text-slate-800 mb-4">
          Contact Support
        </h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Subject
            </label>
            <input
              type="text"
              name="subject"
              value={form.subject}
              onChange={handleChange}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
              placeholder="Brief description of your issue"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Message
            </label>
            <textarea
              name="message"
              value={form.message}
              onChange={handleChange}
              rows={5}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
              placeholder="Describe your issue in detail"
            />
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              className="bg-amber-400 hover:bg-amber-500 text-slate-950 font-semibold px-4 py-2 rounded-lg text-sm transition">
              Send Request
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
