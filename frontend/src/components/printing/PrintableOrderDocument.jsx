import React from "react";

const money = (value) => {
  const number = Number(value || 0);
  return `$${number.toFixed(2)}`;
};

const getOrderShortId = (order) => {
  if (!order?.id) return "N/A";
  return String(order.id).slice(0, 8);
};

const getItemName = (item) => {
  return (
    item?.menu_item?.name ||
    item?.menu_item_name ||
    item?.name ||
    item?.product_name ||
    "Item"
  );
};

const getItemCategoryName = (item) => {
  return (
    item?.menu_item?.category?.name ||
    item?.category?.name ||
    item?.category_name ||
    ""
  );
};

const getItemPrintStation = (item) => {
  return (
    item?.menu_item?.category?.print_station ||
    item?.menu_item?.print_station ||
    item?.category?.print_station ||
    item?.print_station ||
    ""
  );
};

const isBarItem = (item) => {
  const station = String(getItemPrintStation(item)).toUpperCase();
  const category = String(getItemCategoryName(item)).toLowerCase();
  const name = String(getItemName(item)).toLowerCase();

  if (station === "BAR" || station === "DRINKS") return true;

  return (
    category.includes("drink") ||
    category.includes("beverage") ||
    category.includes("bar") ||
    category.includes("beer") ||
    category.includes("wine") ||
    category.includes("cocktail") ||
    name.includes("coke") ||
    name.includes("sprite") ||
    name.includes("water") ||
    name.includes("juice") ||
    name.includes("beer") ||
    name.includes("wine") ||
    name.includes("coffee") ||
    name.includes("tea")
  );
};

const isKitchenItem = (item) => {
  const station = String(getItemPrintStation(item)).toUpperCase();

  if (station === "BAR" || station === "DRINKS" || station === "NONE") {
    return false;
  }

  return !isBarItem(item);
};

const getQuantity = (item) => {
  return Number(item?.quantity || item?.qty || 1);
};

const getUnitPrice = (item) => {
  return Number(
    item?.final_price ??
      item?.unit_price ??
      item?.price ??
      item?.menu_item?.price ??
      0
  );
};

const getLineTotal = (item) => {
  return getQuantity(item) * getUnitPrice(item);
};

const getItems = (order, type) => {
  const items = order?.items || order?.order_items || [];

  if (type === "bar") {
    return items.filter(isBarItem);
  }

  if (type === "kitchen") {
    return items.filter(isKitchenItem);
  }

  return items;
};

const getDocumentTitle = (type) => {
  switch (type) {
    case "kitchen":
      return "KITCHEN TICKET";
    case "bar":
      return "BAR TICKET";
    case "bill":
      return "CUSTOMER BILL";
    case "receipt":
      return "RECEIPT";
    case "copy":
      return "ORDER COPY";
    default:
      return "ORDER";
  }
};

const getOrderType = (order) => {
  return order?.order_type || order?.type || order?.service_type || "Order";
};

const getTableName = (order) => {
  return (
    order?.table?.name ||
    order?.table_name ||
    order?.table_number ||
    order?.table ||
    "-"
  );
};

const getCustomerName = (order) => {
  return order?.customer_name || order?.customer?.name || "";
};

const getServerName = (order) => {
  return (
    order?.server?.email ||
    order?.server?.name ||
    order?.created_by?.email ||
    order?.cashier?.email ||
    ""
  );
};

const formatDateTime = (value) => {
  if (!value) return new Date().toLocaleString();

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);

  return date.toLocaleString();
};

const PrintableOrderDocument = ({ order, type = "receipt" }) => {
  const items = getItems(order, type);
  const title = getDocumentTitle(type);

  const isTicket = type === "kitchen" || type === "bar";
  const showPrices = !isTicket;

  const subtotal = Number(order?.subtotal || 0);
  const tax = Number(order?.tax || 0);
  const serviceCharge = Number(order?.service_charge || 0);
  const tip = Number(order?.tip || 0);
  const discount = Number(order?.discount || 0);
  const total = Number(order?.total || 0);

  return (
    <div className="print-document">
      <div className="receipt-paper">
        <div className="center">
          <div className="brand">BEEPOS</div>
          <div className="subtitle">{title}</div>
        </div>

        <div className="divider" />

        <div className="meta">
          <div>
            <span>Order:</span>
            <strong>#{getOrderShortId(order)}</strong>
          </div>
          <div>
            <span>Type:</span>
            <strong>{getOrderType(order)}</strong>
          </div>
          <div>
            <span>Table:</span>
            <strong>{getTableName(order)}</strong>
          </div>
          {getCustomerName(order) && (
            <div>
              <span>Customer:</span>
              <strong>{getCustomerName(order)}</strong>
            </div>
          )}
          {getServerName(order) && (
            <div>
              <span>Server:</span>
              <strong>{getServerName(order)}</strong>
            </div>
          )}
          <div>
            <span>Date:</span>
            <strong>
              {formatDateTime(order?.created_at || order?.updated_at)}
            </strong>
          </div>
          {order?.status && (
            <div>
              <span>Status:</span>
              <strong>{order.status}</strong>
            </div>
          )}
          {(type === "receipt" || type === "copy") && order?.payment_status && (
            <div>
              <span>Payment:</span>
              <strong>{order.payment_status}</strong>
            </div>
          )}
        </div>

        <div className="divider" />

        <table className="items-table">
          <thead>
            <tr>
              <th className="qty">Qty</th>
              <th>Item</th>
              {showPrices && <th className="amount">Total</th>}
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td
                  colSpan={showPrices ? 3 : 2}
                  className="empty">
                  No items for this document.
                </td>
              </tr>
            ) : (
              items.map((item, index) => (
                <tr key={item.id || index}>
                  <td className="qty">{getQuantity(item)}x</td>
                  <td>
                    <div className="item-name">{getItemName(item)}</div>

                    {item?.notes && (
                      <div className="item-note">Note: {item.notes}</div>
                    )}

                    {item?.special_instructions && (
                      <div className="item-note">
                        Note: {item.special_instructions}
                      </div>
                    )}

                    {showPrices && (
                      <div className="unit-price">
                        {getQuantity(item)} × {money(getUnitPrice(item))}
                      </div>
                    )}
                  </td>
                  {showPrices && (
                    <td className="amount">{money(getLineTotal(item))}</td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>

        {!isTicket && (
          <>
            <div className="divider" />

            <div className="totals">
              <div>
                <span>Subtotal</span>
                <strong>{money(subtotal)}</strong>
              </div>
              <div>
                <span>Tax</span>
                <strong>{money(tax)}</strong>
              </div>
              <div>
                <span>Service</span>
                <strong>{money(serviceCharge)}</strong>
              </div>
              <div>
                <span>Tip</span>
                <strong>{money(tip)}</strong>
              </div>
              <div>
                <span>Discount</span>
                <strong>-{money(discount)}</strong>
              </div>
              <div className="grand-total">
                <span>{type === "bill" ? "TOTAL DUE" : "TOTAL"}</span>
                <strong>{money(total)}</strong>
              </div>
            </div>
          </>
        )}

        <div className="divider" />

        <div className="center footer">
          {isTicket ? (
            <strong>{title} COPY</strong>
          ) : type === "bill" ? (
            <strong>Payment Status: UNPAID</strong>
          ) : (
            <>
              <strong>Thank you!</strong>
              <div>Please come again.</div>
            </>
          )}
        </div>
      </div>

      <style>{`
        .print-document {
          width: 100%;
          display: flex;
          justify-content: center;
          color: #111827;
          font-family: Arial, Helvetica, sans-serif;
        }

        .receipt-paper {
          width: 320px;
          background: #ffffff;
          padding: 18px;
          border: 1px solid #e5e7eb;
          box-shadow: 0 10px 25px rgba(0, 0, 0, 0.08);
        }

        .center {
          text-align: center;
        }

        .brand {
          font-size: 24px;
          font-weight: 900;
          letter-spacing: 2px;
        }

        .subtitle {
          font-size: 13px;
          font-weight: 700;
          margin-top: 4px;
        }

        .divider {
          border-top: 1px dashed #111827;
          margin: 12px 0;
        }

        .meta {
          font-size: 12px;
          display: grid;
          gap: 5px;
        }

        .meta div {
          display: flex;
          justify-content: space-between;
          gap: 10px;
        }

        .meta span {
          color: #4b5563;
        }

        .items-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 12px;
        }

        .items-table th {
          text-align: left;
          padding-bottom: 6px;
          border-bottom: 1px solid #e5e7eb;
        }

        .items-table td {
          vertical-align: top;
          padding: 7px 0;
          border-bottom: 1px solid #f3f4f6;
        }

        .qty {
          width: 38px;
          font-weight: 700;
        }

        .amount {
          text-align: right;
          width: 75px;
          font-weight: 700;
        }

        .item-name {
          font-weight: 700;
        }

        .item-note {
          color: #b91c1c;
          font-size: 11px;
          margin-top: 3px;
        }

        .unit-price {
          color: #6b7280;
          font-size: 11px;
          margin-top: 3px;
        }

        .empty {
          text-align: center;
          color: #6b7280;
          padding: 20px 0 !important;
        }

        .totals {
          font-size: 12px;
          display: grid;
          gap: 6px;
        }

        .totals div {
          display: flex;
          justify-content: space-between;
        }

        .grand-total {
          border-top: 1px solid #111827;
          padding-top: 8px;
          margin-top: 4px;
          font-size: 15px;
          font-weight: 900;
        }

        .footer {
          font-size: 12px;
          line-height: 1.5;
        }

        @media print {
          body * {
            visibility: hidden !important;
          }

          .print-document,
          .print-document * {
            visibility: visible !important;
          }

          .print-document {
            position: absolute;
            left: 0;
            top: 0;
            justify-content: flex-start;
            width: 100%;
          }

          .receipt-paper {
            width: 72mm;
            border: none;
            box-shadow: none;
            padding: 0;
          }

          @page {
            size: 80mm auto;
            margin: 4mm;
          }
        }
      `}</style>
    </div>
  );
};

export default PrintableOrderDocument;
