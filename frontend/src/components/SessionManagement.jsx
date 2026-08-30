import React, { useState, useEffect } from "react";
import api from "../services/api";
import {
  Play,
  StopCircle,
  RefreshCw,
  Wallet,
  Calendar,
  Clock,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";

const SessionManagement = () => {
  const [activeSession, setActiveSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [openingAmount, setOpeningAmount] = useState("0.00");
  const [actionLoading, setActionLoading] = useState(false);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const res = await api.get("/sessions/active/");
      setActiveSession(res.data);
    } catch (err) {
      setActiveSession(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleOpenSession = async () => {
    setActionLoading(true);
    try {
      await api.post("/sessions/", {
        start_amount: parseFloat(openingAmount) || 0,
        status: "OPEN",
      });
      await fetchStatus();
    } catch (err) {
      alert(
        "Error opening session: " +
          (err.response?.data?.detail || "Check server logs")
      );
    } finally {
      setActionLoading(false);
    }
  };

  const handleCloseSession = async () => {
    if (
      !window.confirm(
        "Are you sure you want to close the register? This will end the current business day."
      )
    )
      return;

    setActionLoading(true);
    try {
      // Assuming your backend has a close action or you update status to CLOSED
      await api.patch(`/sessions/${activeSession.id}/`, {
        status: "CLOSED",
        end_time: new Date().toISOString(),
      });
      await fetchStatus();
    } catch (err) {
      alert("Error closing session.");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading)
    return (
      <div className="flex justify-center p-12">
        <RefreshCw
          className="animate-spin text-indigo-600"
          size={32}
        />
      </div>
    );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-black text-slate-900">
          Register Sessions
        </h2>
        {activeSession && (
          <div className="flex items-center gap-2 px-4 py-1.5 bg-green-100 text-green-700 rounded-full text-xs font-black animate-pulse">
            <CheckCircle2 size={14} /> LIVE SESSION
          </div>
        )}
      </div>

      {activeSession ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Session Info Card */}
          <div className="md:col-span-2 bg-white rounded-[32px] p-8 shadow-sm border border-slate-100">
            <div className="flex items-start justify-between mb-8">
              <div>
                <p className="text-slate-400 text-xs font-bold uppercase tracking-widest mb-1">
                  Active Session
                </p>
                <h3 className="text-3xl font-black text-slate-900">
                  #{activeSession.id.toString().padStart(4, "0")}
                </h3>
              </div>
              <div className="bg-indigo-50 p-4 rounded-2xl text-indigo-600">
                <Wallet size={32} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-8 mb-8">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-slate-50 rounded-xl flex items-center justify-center text-slate-400">
                  <Calendar size={20} />
                </div>
                <div>
                  <p className="text-slate-400 text-[10px] font-bold uppercase">
                    Opened Date
                  </p>
                  <p className="text-slate-900 font-bold">
                    {new Date(activeSession.start_time).toLocaleDateString()}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-slate-50 rounded-xl flex items-center justify-center text-slate-400">
                  <Clock size={20} />
                </div>
                <div>
                  <p className="text-slate-400 text-[10px] font-bold uppercase">
                    Start Time
                  </p>
                  <p className="text-slate-900 font-bold">
                    {new Date(activeSession.start_time).toLocaleTimeString()}
                  </p>
                </div>
              </div>
            </div>

            <div className="p-6 bg-slate-50 rounded-2xl flex items-center justify-between">
              <div>
                <p className="text-slate-500 text-xs font-bold">Opening Cash</p>
                <p className="text-2xl font-black text-slate-900">
                  ${parseFloat(activeSession.start_amount).toFixed(2)}
                </p>
              </div>
              <button
                onClick={handleCloseSession}
                disabled={actionLoading}
                className="flex items-center gap-2 bg-red-500 text-white px-8 py-4 rounded-2xl font-black hover:bg-red-600 transition-all shadow-lg shadow-red-100">
                {actionLoading ? (
                  <RefreshCw
                    className="animate-spin"
                    size={20}
                  />
                ) : (
                  <StopCircle size={20} />
                )}
                CLOSE REGISTER
              </button>
            </div>
          </div>

          {/* Quick Stats Card */}
          <div className="bg-indigo-600 rounded-[32px] p-8 text-white shadow-xl shadow-indigo-100 flex flex-col justify-between">
            <div>
              <AlertCircle
                className="mb-4 opacity-50"
                size={32}
              />
              <h4 className="text-xl font-bold mb-2">Session Active</h4>
              <p className="text-indigo-100 text-sm leading-relaxed">
                The register is currently open. You can now process orders in
                the POS Command Center.
              </p>
            </div>
            <div className="mt-8 pt-6 border-t border-indigo-500/50">
              <p className="text-xs font-bold uppercase opacity-60 mb-1">
                Operator
              </p>
              <p className="font-bold">Current Manager</p>
            </div>
          </div>
        </div>
      ) : (
        <div className="max-w-2xl bg-white rounded-[40px] p-12 shadow-xl border border-slate-100 text-center mx-auto">
          <div className="w-24 h-24 bg-slate-100 rounded-full flex items-center justify-center text-slate-400 mx-auto mb-6">
            <Wallet size={48} />
          </div>
          <h3 className="text-3xl font-black text-slate-900 mb-2">
            Register is Closed
          </h3>
          <p className="text-slate-500 mb-10 font-medium">
            Set your opening cash balance to start a new business session.
          </p>

          <div className="max-w-xs mx-auto space-y-4">
            <div className="relative">
              <span className="absolute left-6 top-1/2 -translate-y-1/2 text-slate-400 font-bold">
                $
              </span>
              <input
                type="number"
                value={openingAmount}
                onChange={(e) => setOpeningAmount(e.target.value)}
                className="w-full pl-10 pr-6 py-5 bg-slate-50 border-2 border-slate-100 rounded-3xl text-2xl font-black text-slate-900 focus:border-indigo-500 focus:ring-0 transition-all"
                placeholder="0.00"
              />
            </div>
            <button
              onClick={handleOpenSession}
              disabled={actionLoading}
              className="w-full flex items-center justify-center gap-3 bg-indigo-600 text-white py-5 rounded-3xl font-black text-xl hover:bg-indigo-700 transition-all shadow-xl shadow-indigo-100 active:scale-95">
              {actionLoading ? (
                <RefreshCw
                  className="animate-spin"
                  size={24}
                />
              ) : (
                <Play size={24} />
              )}
              OPEN REGISTER
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default SessionManagement;
