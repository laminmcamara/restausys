import { useEffect, useState } from "react";
import {
  AlertTriangle,
  Banknote,
  CheckCircle2,
  CircleDollarSign,
  Clock3,
  History,
  Info,
  Landmark,
  Loader2,
  Smartphone,
} from "lucide-react";
import api from "../services/api";

const PAYMENT_METHODS = [
  {
    id: "mobile_money",
    label: "Mobile Money",
    icon: <Smartphone size={18} />,
  },
  {
    id: "bank_transfer",
    label: "Bank Transfer",
    icon: <Landmark size={18} />,
  },
  {
    id: "cash",
    label: "Cash / Physical",
    icon: <Banknote size={18} />,
  },
  {
    id: "cheque",
    label: "Cheque",
    icon: <History size={18} />,
  },
];

const normalizeStatus = (value) => {
  return String(value || "")
    .trim()
    .toLowerCase();
};

const formatDate = (value) => {
  if (!value) return "Not available";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Not available";
  }

  return date.toLocaleDateString();
};

const getErrorMessage = (error, fallback) => {
  const data = error?.response?.data;

  if (typeof data === "string") {
    return data;
  }

  if (data?.message) {
    return data.message;
  }

  if (data?.detail) {
    return data.detail;
  }

  if (data?.errors && typeof data.errors === "object") {
    return Object.values(data.errors).flat().join(" ");
  }

  return error?.message || fallback;
};

export default function SubscriptionPage() {
  const [subscription, setSubscription] = useState(null);
  const [plans, setPlans] = useState([]);
  const [selectedPlanId, setSelectedPlanId] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("");
  const [reference, setReference] = useState("");
  const [notes, setNotes] = useState("");

  const [loading, setLoading] = useState(true);
  const [plansLoading, setPlansLoading] = useState(true);
  const [error, setError] = useState("");
  const [submitError, setSubmitError] = useState("");
  const [submitSuccess, setSubmitSuccess] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchSubscription = async () => {
    const response = await api.get("/subscription/");
    const data = response.data?.subscription || response.data;

    setSubscription(data);
    return data;
  };

  const fetchPlans = async () => {
    const response = await api.get("/plans/");
    const data = response.data?.results || response.data || [];
    const nextPlans = Array.isArray(data) ? data : [];

    setPlans(nextPlans);
    return nextPlans;
  };

  useEffect(() => {
    let isMounted = true;

    async function loadPage() {
      setLoading(true);
      setPlansLoading(true);
      setError("");

      try {
        const [subscriptionResult, plansResult] = await Promise.all([
          fetchSubscription(),
          fetchPlans(),
        ]);

        if (!isMounted) return;

        const pendingPlanId =
          subscriptionResult?.pending_plan?.id ||
          subscriptionResult?.pending_plan_id ||
          "";

        if (pendingPlanId) {
          setSelectedPlanId(String(pendingPlanId));
        } else if (plansResult.length === 1) {
          setSelectedPlanId(String(plansResult[0].id));
        }
      } catch (requestError) {
        if (!isMounted) return;

        setError(
          getErrorMessage(
            requestError,
            "Unable to load subscription information."
          )
        );
      } finally {
        if (isMounted) {
          setLoading(false);
          setPlansLoading(false);
        }
      }
    }

    loadPage();

    return () => {
      isMounted = false;
    };
  }, []);

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!selectedPlanId) {
      setSubmitError("Please select a plan.");
      return;
    }

    if (!paymentMethod) {
      setSubmitError("Please select a payment method.");
      return;
    }

    if (!reference.trim()) {
      setSubmitError("Please enter your payment reference.");
      return;
    }

    setIsSubmitting(true);
    setSubmitError("");
    setSubmitSuccess("");

    try {
      const response = await api.post("/subscription/submit-request/", {
        plan_id: selectedPlanId,
        offline_payment_method: paymentMethod,
        offline_payment_reference: reference.trim(),
        offline_payment_notes: notes.trim(),
      });

      const pendingPlan = response.data?.pending_plan;

      setSubmitSuccess(
        pendingPlan?.name
          ? `Your ${pendingPlan.name} plan request was submitted for verification.`
          : "Your subscription request was submitted for verification."
      );

      setReference("");
      setNotes("");

      await fetchSubscription();
    } catch (requestError) {
      setSubmitError(
        getErrorMessage(
          requestError,
          "Unable to submit your renewal request. Please try again."
        )
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Loader2 className="h-9 w-9 animate-spin text-amber-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-5xl p-6">
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-red-700">
          {error}
        </div>
      </div>
    );
  }

  const status = normalizeStatus(subscription?.status);
  const daysRemaining = Number(subscription?.days_remaining || 0);
  const isActive = Boolean(subscription?.is_active);
  const isExpired = status === "expired" || !isActive;

  const pendingPlan =
    subscription?.pending_plan ||
    (subscription?.pending_plan_name
      ? { name: subscription.pending_plan_name }
      : null);

  const periodEnd = subscription?.current_period_end || subscription?.trial_end;

  return (
    <div className="mx-auto max-w-6xl space-y-8 p-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Subscription</h1>
          <p className="text-slate-500">
            Select a plan after your trial and submit your payment details.
          </p>
        </div>

        <div
          className={`inline-flex w-fit items-center gap-2 rounded-full px-4 py-2 text-sm font-bold ${
            isExpired
              ? "bg-red-100 text-red-700"
              : daysRemaining <= 7
              ? "bg-amber-100 text-amber-700"
              : "bg-green-100 text-green-700"
          }`}>
          {isExpired ? <AlertTriangle size={16} /> : <CheckCircle2 size={16} />}

          {isExpired
            ? "Access requires a plan"
            : `${daysRemaining} days remaining`}
        </div>
      </div>

      {pendingPlan && (
        <div className="flex gap-3 rounded-2xl border border-blue-200 bg-blue-50 p-4 text-blue-800">
          <Clock3
            className="mt-0.5 shrink-0"
            size={20}
          />
          <div>
            <p className="font-bold">Verification pending</p>
            <p className="mt-1 text-sm">
              Your request for the {pendingPlan.name} plan has been submitted.
              Access will be restored after payment verification.
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        <aside className="space-y-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm font-semibold uppercase tracking-wider text-slate-400">
              Current access
            </p>

            <p className="mt-2 text-3xl font-bold text-slate-900">
              {subscription?.plan_name || "Free Trial"}
            </p>

            <p className="mt-2 text-sm text-slate-500">
              {isExpired
                ? "Your trial or subscription has expired."
                : `Period ends on ${formatDate(periodEnd)}.`}
            </p>

            <div className="mt-6 border-t border-slate-100 pt-6">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-500">Status</span>
                <span className="font-bold capitalize text-slate-900">
                  {status || "Unknown"}
                </span>
              </div>

              <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
                <div
                  className={`h-full rounded-full ${
                    isExpired
                      ? "bg-red-500"
                      : daysRemaining <= 7
                      ? "bg-amber-500"
                      : "bg-green-500"
                  }`}
                  style={{
                    width: `${Math.max(
                      0,
                      Math.min(100, (daysRemaining / 30) * 100)
                    )}%`,
                  }}
                />
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6">
            <div className="flex gap-3">
              <Info
                className="shrink-0 text-amber-600"
                size={20}
              />
              <p className="text-sm text-amber-800">
                Offline payment requests are activated after verification. Keep
                your transaction reference or receipt available.
              </p>
            </div>
          </div>
        </aside>

        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm lg:col-span-2">
          <div className="border-b border-slate-100 p-6">
            <h2 className="text-lg font-bold text-slate-900">
              Choose your plan
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Select the plan that fits your restaurant, then submit payment
              details for approval.
            </p>
          </div>

          <form
            onSubmit={handleSubmit}
            className="space-y-6 p-6">
            {submitSuccess && (
              <div className="rounded-xl border border-green-200 bg-green-50 p-4 text-sm text-green-700">
                {submitSuccess}
              </div>
            )}

            {submitError && (
              <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                {submitError}
              </div>
            )}

            <div>
              <p className="mb-3 text-sm font-semibold text-slate-700">
                Available plans
              </p>

              {plansLoading ? (
                <div className="flex justify-center py-10">
                  <Loader2 className="h-7 w-7 animate-spin text-amber-600" />
                </div>
              ) : plans.length === 0 ? (
                <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
                  No subscription plans are available. Please contact support.
                </div>
              ) : (
                <div className="grid gap-4 md:grid-cols-2">
                  {plans.map((plan) => {
                    const isSelected = String(plan.id) === selectedPlanId;

                    return (
                      <button
                        key={plan.id}
                        type="button"
                        onClick={() => setSelectedPlanId(String(plan.id))}
                        className={`rounded-2xl border-2 p-5 text-left transition ${
                          isSelected
                            ? "border-amber-500 bg-amber-50 ring-2 ring-amber-100"
                            : "border-slate-200 bg-white hover:border-slate-300"
                        }`}>
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <h3 className="text-lg font-bold text-slate-900">
                              {plan.name}
                            </h3>
                            <p className="mt-1 text-sm text-slate-500">
                              {plan.max_users} users · {plan.max_tables} tables
                            </p>
                          </div>

                          {isSelected && (
                            <CheckCircle2
                              className="shrink-0 text-amber-600"
                              size={20}
                            />
                          )}
                        </div>

                        <div className="mt-4 flex items-center gap-2 text-slate-900">
                          <CircleDollarSign size={18} />
                          <span className="text-xl font-bold">
                            {plan.monthly_price}
                          </span>
                          <span className="text-sm text-slate-500">
                            / month
                          </span>
                        </div>

                        <div className="mt-4 space-y-1 text-xs text-slate-600">
                          <p>
                            Inventory:{" "}
                            {plan.allow_inventory ? "Included" : "Not included"}
                          </p>
                          <p>
                            Analytics:{" "}
                            {plan.allow_analytics ? "Included" : "Not included"}
                          </p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            <div>
              <label className="mb-3 block text-sm font-semibold text-slate-700">
                Payment method
              </label>

              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                {PAYMENT_METHODS.map((method) => {
                  const isSelected = paymentMethod === method.id;

                  return (
                    <button
                      key={method.id}
                      type="button"
                      onClick={() => setPaymentMethod(method.id)}
                      className={`flex flex-col items-center justify-center gap-2 rounded-xl border-2 p-4 transition ${
                        isSelected
                          ? "border-amber-500 bg-amber-50 text-amber-700"
                          : "border-slate-100 text-slate-500 hover:border-slate-200"
                      }`}>
                      {method.icon}
                      <span className="text-xs font-bold">{method.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="space-y-4 rounded-xl border border-slate-200 bg-slate-50 p-5">
              <div>
                <label
                  htmlFor="payment-reference"
                  className="mb-1 block text-xs font-bold uppercase text-slate-500">
                  Transaction reference
                </label>

                <input
                  id="payment-reference"
                  type="text"
                  value={reference}
                  onChange={(event) => setReference(event.target.value)}
                  placeholder="Enter your payment receipt or transaction reference"
                  className="w-full rounded-lg border border-slate-300 bg-white p-3 font-mono outline-none transition focus:ring-2 focus:ring-amber-500"
                  required
                />
              </div>

              <div>
                <label
                  htmlFor="payment-notes"
                  className="mb-1 block text-xs font-bold uppercase text-slate-500">
                  Notes (optional)
                </label>

                <textarea
                  id="payment-notes"
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  placeholder="Add useful payment or transfer information"
                  rows={3}
                  className="w-full rounded-lg border border-slate-300 bg-white p-3 outline-none transition focus:ring-2 focus:ring-amber-500"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={
                !selectedPlanId ||
                !paymentMethod ||
                !reference.trim() ||
                isSubmitting ||
                plans.length === 0
              }
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-slate-900 py-4 font-bold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-200">
              {isSubmitting ? (
                <>
                  <Loader2
                    className="animate-spin"
                    size={18}
                  />
                  Submitting request...
                </>
              ) : (
                "Submit plan and payment request"
              )}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
