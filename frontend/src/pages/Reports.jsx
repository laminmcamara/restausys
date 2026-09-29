import React, { useEffect, useMemo, useState } from "react";

import {
  BarChart,
  Bar,
  CartesianGrid,
  Cell,
  Legend,
  LineChart,
  Line,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  CalendarDays,
  ClipboardList,
  DollarSign,
  RefreshCw,
  ShoppingBag,
  TrendingUp,
  Utensils,
} from "lucide-react";

import api from "../services/api";

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

const COLORS = [
  "#2563eb",
  "#16a34a",
  "#f97316",
  "#dc2626",
  "#7c3aed",
  "#0891b2",
];

function createEmptyReport() {
  return {
    summary: {
      weekly_sales: 0,
      monthly_sales: 0,
      weekly_orders: 0,
      monthly_orders: 0,
      average_order_value: 0,
      active_tables: 0,
    },
    sales_by_day: [],
    orders_by_status: [],
    top_items: [],
    staff_performance: [],
    recent_orders: [],
  };
}

function formatInputDate(date) {
  const year = date.getFullYear();

  const month = String(date.getMonth() + 1).padStart(2, "0");

  const day = String(date.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

function getInitialDateRange() {
  const today = new Date();

  const sevenDaysAgo = new Date(today);

  sevenDaysAgo.setDate(today.getDate() - 6);

  return {
    startDate: formatInputDate(sevenDaysAgo),
    endDate: formatInputDate(today),
  };
}

function toNumber(value) {
  const number = Number(value);

  return Number.isFinite(number) ? number : 0;
}

function normalizeReport(data) {
  const emptyReport = createEmptyReport();

  const summary = data?.summary || {};

  return {
    summary: {
      weekly_sales: toNumber(summary.weekly_sales),
      monthly_sales: toNumber(summary.monthly_sales),
      weekly_orders: toNumber(summary.weekly_orders),
      monthly_orders: toNumber(summary.monthly_orders),
      average_order_value: toNumber(summary.average_order_value),
      active_tables: toNumber(summary.active_tables),
    },

    sales_by_day: Array.isArray(data?.sales_by_day)
      ? data.sales_by_day.map((item) => ({
          date: item.date || "",
          sales: toNumber(item.sales),
        }))
      : emptyReport.sales_by_day,

    orders_by_status: Array.isArray(data?.orders_by_status)
      ? data.orders_by_status.map((item) => ({
          name: item.name || item.status || "Unknown",
          value: toNumber(item.value ?? item.count),
        }))
      : emptyReport.orders_by_status,

    top_items: Array.isArray(data?.top_items)
      ? data.top_items.map((item) => ({
          product_id: item.product_id || null,
          product_name: item.product_name || item.name || "Unnamed product",
          quantity: toNumber(item.quantity),
          revenue: toNumber(item.revenue),
        }))
      : emptyReport.top_items,

    staff_performance: Array.isArray(data?.staff_performance)
      ? data.staff_performance.map((staff) => ({
          id: staff.id || null,
          name: staff.name || staff.staff_name || "Unknown Staff",
          orders: toNumber(staff.orders ?? staff.order_count),
          sales: toNumber(staff.sales ?? staff.total_sales),
          average_order_value: toNumber(
            staff.average_order_value ?? staff.average_order
          ),
          pending_orders: toNumber(staff.pending_orders),
          cancelled_orders: toNumber(staff.cancelled_orders),
        }))
      : emptyReport.staff_performance,

    recent_orders: Array.isArray(data?.recent_orders)
      ? data.recent_orders.map((order) => ({
          id: order.id || null,
          order_number: order.order_number || null,
          short_id: order.short_id || null,
          table: order.table || null,
          table_number: order.table_number || order.table_name || null,
          status: order.status || "UNKNOWN",
          total: toNumber(
            order.total ?? order.total_price ?? order.total_amount
          ),
          created_at: order.created_at || null,
        }))
      : emptyReport.recent_orders,
  };
}

function Card({ title, value, subtitle, icon: Icon, accent = "blue" }) {
  const accentClasses = {
    blue: "bg-blue-50 text-blue-600",
    green: "bg-green-50 text-green-600",
    orange: "bg-orange-50 text-orange-600",
    purple: "bg-purple-50 text-purple-600",
    red: "bg-red-50 text-red-600",
    cyan: "bg-cyan-50 text-cyan-600",
  };

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-gray-500">{title}</p>

          <p className="mt-2 text-2xl font-bold text-gray-900">{value}</p>

          {subtitle ? (
            <p className="mt-1 text-xs text-gray-500">{subtitle}</p>
          ) : null}
        </div>

        {Icon ? (
          <div
            className={`flex h-11 w-11 items-center justify-center rounded-xl ${
              accentClasses[accent] || accentClasses.blue
            }`}>
            <Icon size={22} />
          </div>
        ) : null}
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const normalized = String(status || "")
    .trim()
    .toUpperCase();

  const labels = {
    DRAFT: "Draft",
    PLACED: "Placed",
    IN_PROGRESS: "In Progress",
    PREPARING: "Preparing",
    READY: "Ready",
    SERVED: "Served",
    COMPLETED: "Completed",
    PAID: "Paid",
    PENDING: "Pending",
    CANCELED: "Canceled",
    CANCELLED: "Canceled",
  };

  const classes = {
    DRAFT: "bg-gray-100 text-gray-700",
    PLACED: "bg-blue-100 text-blue-700",
    IN_PROGRESS: "bg-orange-100 text-orange-700",
    PREPARING: "bg-orange-100 text-orange-700",
    READY: "bg-cyan-100 text-cyan-700",
    SERVED: "bg-purple-100 text-purple-700",
    COMPLETED: "bg-green-100 text-green-700",
    PAID: "bg-green-100 text-green-700",
    PENDING: "bg-yellow-100 text-yellow-700",
    CANCELED: "bg-red-100 text-red-700",
    CANCELLED: "bg-red-100 text-red-700",
  };

  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
        classes[normalized] || "bg-gray-100 text-gray-700"
      }`}>
      {labels[normalized] || status || "Unknown"}
    </span>
  );
}

function EmptyState({ message }) {
  return (
    <div className="flex min-h-48 items-center justify-center rounded-xl border border-dashed border-gray-300 bg-gray-50 p-6 text-center text-sm text-gray-500">
      {message}
    </div>
  );
}

function getTableLabel(order) {
  if (order.table_number) {
    return `Table ${order.table_number}`;
  }

  if (typeof order.table === "string") {
    return order.table;
  }

  if (order.table && typeof order.table === "object") {
    return order.table.table_number || order.table.name || "N/A";
  }

  return "N/A";
}

function getOrderLabel(order) {
  return order.order_number || order.short_id || order.id || "Unknown";
}

function Reports() {
  const initialDates = useMemo(() => getInitialDateRange(), []);

  const [startDate, setStartDate] = useState(initialDates.startDate);

  const [endDate, setEndDate] = useState(initialDates.endDate);

  const [report, setReport] = useState(createEmptyReport());

  const [loading, setLoading] = useState(false);

  const [error, setError] = useState("");

  const summary = report.summary;

  const hasSalesData = report.sales_by_day.length > 0;

  const hasStatusData = report.orders_by_status.length > 0;

  async function fetchReports() {
    setLoading(true);
    setError("");

    try {
      const response = await api.get("/reports/", {
        params: {
          start_date: startDate,
          end_date: endDate,
        },
        withCredentials: true,
      });

      const data = response.data || {};

      console.log("REPORTS API RESPONSE:", data);

      setReport(normalizeReport(data));
    } catch (err) {
      console.error("Failed to load reports:", err);

      setReport(createEmptyReport());

      setError("Could not load live report data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchReports();

    // The initial report should load once.
    // Clicking Apply loads the selected range.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleApplyFilters(event) {
    event.preventDefault();
    fetchReports();
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reports</h1>

          <p className="mt-1 text-sm text-gray-500">
            Track sales, orders, top items, and staff performance.
          </p>
        </div>

        <form
          onSubmit={handleApplyFilters}
          className="flex flex-col gap-3 rounded-2xl border border-gray-200 bg-white p-3 shadow-sm sm:flex-row sm:items-end">
          <div>
            <label className="mb-1 block text-xs font-semibold text-gray-500">
              Start Date
            </label>

            <input
              type="date"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
              className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold text-gray-500">
              End Date
            </label>

            <input
              type="date"
              value={endDate}
              onChange={(event) => setEndDate(event.target.value)}
              className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60">
            <RefreshCw
              size={16}
              className={loading ? "animate-spin" : ""}
            />

            {loading ? "Loading..." : "Apply"}
          </button>
        </form>
      </div>

      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card
          title="Weekly Sales"
          value={currency.format(summary.weekly_sales)}
          subtitle="Current week"
          icon={TrendingUp}
          accent="green"
        />

        <Card
          title="Monthly Sales"
          value={currency.format(summary.monthly_sales)}
          subtitle="Current month"
          icon={DollarSign}
          accent="blue"
        />

        <Card
          title="Weekly Orders"
          value={summary.weekly_orders.toLocaleString()}
          subtitle="Orders this week"
          icon={ShoppingBag}
          accent="orange"
        />

        <Card
          title="Monthly Orders"
          value={summary.monthly_orders.toLocaleString()}
          subtitle="Orders this month"
          icon={ClipboardList}
          accent="purple"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card
          title="Average Order Value"
          value={currency.format(summary.average_order_value)}
          subtitle={`${startDate} to ${endDate}`}
          icon={CalendarDays}
          accent="cyan"
        />

        <Card
          title="Active Tables"
          value={summary.active_tables.toLocaleString()}
          subtitle="Currently in use"
          icon={Utensils}
          accent="red"
        />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="mb-5">
            <h2 className="text-lg font-bold text-gray-900">Sales Trend</h2>

            <p className="text-sm text-gray-500">
              Daily sales from paid orders for the selected period.
            </p>
          </div>

          {hasSalesData ? (
            <div className="h-80">
              <ResponsiveContainer
                width="100%"
                height="100%">
                <LineChart data={report.sales_by_day}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="#e5e7eb"
                  />

                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 12 }}
                  />

                  <YAxis tick={{ fontSize: 12 }} />

                  <Tooltip
                    formatter={(value) => currency.format(toNumber(value))}
                  />

                  <Legend />

                  <Line
                    type="monotone"
                    dataKey="sales"
                    name="Sales"
                    stroke="#2563eb"
                    strokeWidth={3}
                    dot={{ r: 4 }}
                    activeDot={{ r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState message="No sales trend data found for this period." />
          )}
        </div>

        <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="mb-5">
            <h2 className="text-lg font-bold text-gray-900">
              Orders by Status
            </h2>

            <p className="text-sm text-gray-500">
              Order count grouped by current status.
            </p>
          </div>

          {hasStatusData ? (
            <div className="h-80">
              <ResponsiveContainer
                width="100%"
                height="100%">
                <PieChart>
                  <Pie
                    data={report.orders_by_status}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={95}
                    label>
                    {report.orders_by_status.map((entry, index) => (
                      <Cell
                        key={`${entry.name}-${index}`}
                        fill={COLORS[index % COLORS.length]}
                      />
                    ))}
                  </Pie>

                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState message="No order status data found for this period." />
          )}
        </div>
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="mb-5">
          <h2 className="text-lg font-bold text-gray-900">Top Selling Items</h2>

          <p className="text-sm text-gray-500">
            Best-selling items from paid orders.
          </p>
        </div>

        {report.top_items.length > 0 ? (
          <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
            <div className="h-80">
              <ResponsiveContainer
                width="100%"
                height="100%">
                <BarChart data={report.top_items}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="#e5e7eb"
                  />

                  <XAxis
                    dataKey="product_name"
                    tick={{ fontSize: 12 }}
                  />

                  <YAxis tick={{ fontSize: 12 }} />

                  <Tooltip />

                  <Legend />

                  <Bar
                    dataKey="quantity"
                    name="Quantity Sold"
                    fill="#16a34a"
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b text-gray-500">
                    <th className="py-3 font-semibold">Item</th>

                    <th className="py-3 font-semibold">Qty</th>

                    <th className="py-3 font-semibold">Revenue</th>
                  </tr>
                </thead>

                <tbody>
                  {report.top_items.map((item, index) => (
                    <tr
                      key={`${item.product_id || "product"}-${
                        item.product_name
                      }-${index}`}
                      className="border-b last:border-0">
                      <td className="py-3 font-medium text-gray-900">
                        {item.product_name}
                      </td>

                      <td className="py-3 text-gray-600">
                        {item.quantity.toLocaleString()}
                      </td>

                      <td className="py-3 text-gray-600">
                        {currency.format(item.revenue)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <EmptyState message="No top selling items found for this period." />
        )}
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="mb-5">
          <h2 className="text-lg font-bold text-gray-900">Staff Performance</h2>

          <p className="text-sm text-gray-500">
            Staff order volume, sales, and order status breakdown.
          </p>
        </div>

        {report.staff_performance.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b text-gray-500">
                  <th className="py-3 font-semibold">Staff</th>

                  <th className="py-3 font-semibold">Orders</th>

                  <th className="py-3 font-semibold">Sales</th>

                  <th className="py-3 font-semibold">Avg Order</th>

                  <th className="py-3 font-semibold">Pending</th>

                  <th className="py-3 font-semibold">Cancelled</th>
                </tr>
              </thead>

              <tbody>
                {report.staff_performance.map((staff) => (
                  <tr
                    key={staff.id || staff.name}
                    className="border-b last:border-0">
                    <td className="py-3 font-medium text-gray-900">
                      <div className="flex items-center gap-2">
                        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-100 text-xs font-bold text-gray-600">
                          {String(staff.name || "U")
                            .slice(0, 1)
                            .toUpperCase()}
                        </span>

                        {staff.name || "Unknown Staff"}
                      </div>
                    </td>

                    <td className="py-3 text-gray-600">
                      {staff.orders.toLocaleString()}
                    </td>

                    <td className="py-3 text-gray-600">
                      {currency.format(staff.sales)}
                    </td>

                    <td className="py-3 text-gray-600">
                      {currency.format(staff.average_order_value)}
                    </td>

                    <td className="py-3 text-gray-600">
                      {staff.pending_orders.toLocaleString()}
                    </td>

                    <td className="py-3 text-gray-600">
                      {staff.cancelled_orders.toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState message="No staff performance data found for this period." />
        )}
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="mb-5">
          <h2 className="text-lg font-bold text-gray-900">Recent Orders</h2>

          <p className="text-sm text-gray-500">
            Latest orders created in the selected period.
          </p>
        </div>

        {report.recent_orders.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b text-gray-500">
                  <th className="py-3 font-semibold">Order</th>

                  <th className="py-3 font-semibold">Table</th>

                  <th className="py-3 font-semibold">Status</th>

                  <th className="py-3 font-semibold">Total</th>

                  <th className="py-3 font-semibold">Created</th>
                </tr>
              </thead>

              <tbody>
                {report.recent_orders.map((order) => (
                  <tr
                    key={order.id || order.order_number}
                    className="border-b last:border-0">
                    <td className="py-3 font-medium text-gray-900">
                      #{getOrderLabel(order)}
                    </td>

                    <td className="py-3 text-gray-600">
                      {getTableLabel(order)}
                    </td>

                    <td className="py-3">
                      <StatusBadge status={order.status} />
                    </td>

                    <td className="py-3 text-gray-600">
                      {currency.format(order.total)}
                    </td>

                    <td className="py-3 text-gray-600">
                      {order.created_at || "N/A"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState message="No recent orders found for this period." />
        )}
      </div>
    </div>
  );
}

export default Reports;
