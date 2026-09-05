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
  Users,
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

const today = new Date();
const sevenDaysAgo = new Date();
sevenDaysAgo.setDate(today.getDate() - 6);

function formatInputDate(date) {
  return date.toISOString().slice(0, 10);
}

const demoReport = {
  summary: {
    weekly_sales: 1840.25,
    monthly_sales: 6840.75,
    weekly_orders: 92,
    monthly_orders: 310,
    average_order_value: 20.75,
    active_tables: 8,
  },
  sales_by_day: [
    { date: "Mon", sales: 320 },
    { date: "Tue", sales: 410 },
    { date: "Wed", sales: 380 },
    { date: "Thu", sales: 520 },
    { date: "Fri", sales: 760 },
    { date: "Sat", sales: 890 },
    { date: "Sun", sales: 640 },
  ],
  orders_by_status: [
    { name: "Completed", value: 86 },
    { name: "Pending", value: 14 },
    { name: "Preparing", value: 18 },
    { name: "Cancelled", value: 8 },
  ],
  top_items: [
    { name: "Chicken Burger", quantity: 42, revenue: 504 },
    { name: "Jollof Rice", quantity: 38, revenue: 456 },
    { name: "Grilled Fish", quantity: 25, revenue: 375 },
    { name: "Beef Shawarma", quantity: 22, revenue: 242 },
    { name: "Fresh Juice", quantity: 31, revenue: 155 },
  ],
  staff_performance: [
    {
      id: 1,
      name: "Mary Johnson",
      orders: 28,
      sales: 620.5,
      average_order_value: 22.16,
      pending_orders: 3,
      cancelled_orders: 1,
    },
    {
      id: 2,
      name: "James Brown",
      orders: 22,
      sales: 480,
      average_order_value: 21.82,
      pending_orders: 2,
      cancelled_orders: 0,
    },
    {
      id: 3,
      name: "Admin User",
      orders: 14,
      sales: 310.25,
      average_order_value: 22.16,
      pending_orders: 1,
      cancelled_orders: 2,
    },
  ],
  recent_orders: [
    {
      id: 1001,
      table: "Table 1",
      status: "completed",
      total: 38.5,
      created_at: "2026-08-11 12:30",
    },
    {
      id: 1002,
      table: "Table 4",
      status: "preparing",
      total: 24,
      created_at: "2026-08-11 12:45",
    },
    {
      id: 1003,
      table: "Table 7",
      status: "pending",
      total: 18.75,
      created_at: "2026-08-11 13:05",
    },
    {
      id: 1004,
      table: "Table 3",
      status: "completed",
      total: 52.5,
      created_at: "2026-08-11 13:20",
    },
  ],
};

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
  const normalized = String(status || "").toLowerCase();

  const classes = {
    completed: "bg-green-100 text-green-700",
    paid: "bg-green-100 text-green-700",
    pending: "bg-yellow-100 text-yellow-700",
    preparing: "bg-orange-100 text-orange-700",
    cancelled: "bg-red-100 text-red-700",
    canceled: "bg-red-100 text-red-700",
  };

  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
        classes[normalized] || "bg-gray-100 text-gray-700"
      }`}>
      {status || "Unknown"}
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

function Reports() {
  const [startDate, setStartDate] = useState(formatInputDate(sevenDaysAgo));
  const [endDate, setEndDate] = useState(formatInputDate(today));
  const [report, setReport] = useState(demoReport);
  const [loading, setLoading] = useState(false);
  const [usingDemoData, setUsingDemoData] = useState(false);
  const [error, setError] = useState("");

  const summary = report.summary || demoReport.summary;

  const hasSalesData = useMemo(() => {
    return Array.isArray(report.sales_by_day) && report.sales_by_day.length > 0;
  }, [report.sales_by_day]);

  const hasStatusData = useMemo(() => {
    return (
      Array.isArray(report.orders_by_status) &&
      report.orders_by_status.length > 0
    );
  }, [report.orders_by_status]);

  async function fetchReports() {
    setLoading(true);
    setError("");

    try {
      const response = await api.get("/reports/", {
        params: {
          start_date: startDate,
          end_date: endDate,
        },
      });

      const data = response.data || {};

      setReport({
        summary: {
          ...demoReport.summary,
          ...(data.summary || {}),
        },
        sales_by_day: data.sales_by_day || [],
        orders_by_status: data.orders_by_status || [],
        top_items: data.top_items || [],
        staff_performance: data.staff_performance || [],
        recent_orders: data.recent_orders || [],
      });

      setUsingDemoData(false);
    } catch (err) {
      console.error("Failed to load reports:", err);
      setReport(demoReport);
      setUsingDemoData(true);
      setError("Could not load live report data. Showing demo data instead.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchReports();
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
        <div className="rounded-xl border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm text-yellow-800">
          {error}
        </div>
      ) : null}

      {usingDemoData ? (
        <div className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
          Demo report data is currently displayed. Connect the backend reports
          endpoint to show live data.
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card
          title="Weekly Sales"
          value={currency.format(Number(summary.weekly_sales || 0))}
          subtitle="Current week"
          icon={TrendingUp}
          accent="green"
        />
        <Card
          title="Monthly Sales"
          value={currency.format(Number(summary.monthly_sales || 0))}
          subtitle="Current month"
          icon={DollarSign}
          accent="blue"
        />
        <Card
          title="Weekly Orders"
          value={Number(summary.weekly_orders || 0).toLocaleString()}
          subtitle="Orders this week"
          icon={ShoppingBag}
          accent="orange"
        />
        <Card
          title="Monthly Orders"
          value={Number(summary.monthly_orders || 0).toLocaleString()}
          subtitle="Orders this month"
          icon={ClipboardList}
          accent="purple"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card
          title="Average Order Value"
          value={currency.format(Number(summary.average_order_value || 0))}
          subtitle={`${startDate} to ${endDate}`}
          icon={CalendarDays}
          accent="cyan"
        />
        <Card
          title="Active Tables"
          value={Number(summary.active_tables || 0).toLocaleString()}
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
              Daily completed/paid order sales for the selected period.
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
                    formatter={(value) => currency.format(Number(value || 0))}
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
            Best-selling menu items from completed/paid orders.
          </p>
        </div>

        {report.top_items && report.top_items.length > 0 ? (
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
                    dataKey="name"
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
                  {report.top_items.map((item) => (
                    <tr
                      key={item.product_name}
                      className="border-b last:border-0">
                      <td className="py-3 font-medium text-gray-900">
                        {item.product_name}
                      </td>
                      <td className="py-3 text-gray-600">
                        {Number(item.quantity || 0).toLocaleString()}
                      </td>
                      <td className="py-3 text-gray-600">
                        {currency.format(Number(item.revenue || 0))}
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

        {report.staff_performance && report.staff_performance.length > 0 ? (
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
                      {Number(staff.orders || 0).toLocaleString()}
                    </td>
                    <td className="py-3 text-gray-600">
                      {currency.format(Number(staff.sales || 0))}
                    </td>
                    <td className="py-3 text-gray-600">
                      {currency.format(Number(staff.average_order_value || 0))}
                    </td>
                    <td className="py-3 text-gray-600">
                      {Number(staff.pending_orders || 0).toLocaleString()}
                    </td>
                    <td className="py-3 text-gray-600">
                      {Number(staff.cancelled_orders || 0).toLocaleString()}
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

        {report.recent_orders && report.recent_orders.length > 0 ? (
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
                    key={order.id}
                    className="border-b last:border-0">
                    <td className="py-3 font-medium text-gray-900">
                      #{order.id}
                    </td>
                    <td className="py-3 text-gray-600">
                      {order.table || "N/A"}
                    </td>
                    <td className="py-3">
                      <StatusBadge status={order.status} />
                    </td>
                    <td className="py-3 text-gray-600">
                      {currency.format(Number(order.total || 0))}
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
