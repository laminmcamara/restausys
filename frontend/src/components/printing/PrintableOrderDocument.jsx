import React from "react";

const PrintableOrderDocument = ({ order, type = "receipt" }) => {
  if (!order) return null;

  const userData = JSON.parse(localStorage.getItem("user") || "{}");
  const restaurantName =
    order.restaurant_name || userData.restaurant_name || "BEEPOS RESTAURANT";
  const isKitchen = type === "kitchen" || type === "bar";

  // Normalize items to handle different API response structures
  const rawItems = order.items || order.order_items || [];

  // 1. ITEM GROUPING (Combines identical items with same modifiers)
  const groupedItems = rawItems.reduce((acc, item) => {
    const productName =
      item.product_name || item.product?.name || "Unknown Item";
    // Normalize modifiers to strings for key comparison
    const mods = Array.isArray(item.modifiers)
      ? item.modifiers.map((m) => (typeof m === "string" ? m : m.name || ""))
      : [];
    const modifierString = JSON.stringify(mods);
    const key = `${productName}-${modifierString}-${item.notes || ""}`;

    if (!acc[key]) {
      acc[key] = {
        ...item,
        display_name: productName,
        display_mods: mods,
        quantity: Number(item.quantity || 1),
      };
    } else {
      acc[key].quantity += Number(item.quantity || 1);
    }
    return acc;
  }, {});

  const displayItems = Object.values(groupedItems);

  // 2. TABLE IDENTIFIER
  let tableDisplay = "T/O";
  if (order.table_name || order.table_number) {
    const val = String(order.table_name || order.table_number);
    tableDisplay = val.toUpperCase().startsWith("T") ? val : `T-${val}`;
  } else if (order.customer_name && order.customer_name !== "Guest") {
    tableDisplay = order.customer_name.toUpperCase();
  }

  const formatMoney = (val) => Number(val || 0).toFixed(2);
  const shortId = String(order.display_id || order.id)
    .split("-")
    .pop()
    ?.slice(-4)
    .toUpperCase();

  return (
    <div className="printable-document">
      {/* WATERMARK FOR CANCELED ORDERS */}
      {order.status === "CANCELED" && (
        <div className="void-watermark">VOID / CANCELED</div>
      )}

      {isKitchen ? (
        /* KITCHEN TICKET - High contrast, large fonts */
        <div className="kitchen-ticket">
          <div className="kitchen-header">
            <h1 className={tableDisplay.length > 5 ? "text-xl" : ""}>
              {tableDisplay}
            </h1>
            <div className="order-meta">
              <span>#{shortId}</span>
              <span>
                {new Date(order.created_at || Date.now()).toLocaleTimeString(
                  [],
                  {
                    hour: "2-digit",
                    minute: "2-digit",
                  }
                )}
              </span>
            </div>
          </div>

          <div className="item-list">
            {displayItems.map((item, idx) => (
              <div
                key={idx}
                className="kitchen-item">
                <span className="qty">{item.quantity}x</span>
                <div className="details">
                  <span className="name">{item.display_name}</span>
                  {item.display_mods?.map((m, i) => (
                    <span
                      key={i}
                      className="mod">
                      • {m}
                    </span>
                  ))}
                  {(item.notes || item.note) && (
                    <span className="item-note">
                      ** {item.notes || item.note}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        /* CUSTOMER RECEIPT - Detailed breakdown */
        <div className="customer-receipt">
          <div className="receipt-header">
            <h2 className="restaurant-name">{restaurantName}</h2>
            <p className="receipt-subtext">Order #{shortId}</p>
            <p className="receipt-subtext">
              {new Date(order.created_at || Date.now()).toLocaleString()}
            </p>
            <p className="receipt-subtext font-bold">Table: {tableDisplay}</p>
          </div>

          <div className="receipt-divider"></div>

          <table className="receipt-table">
            <thead>
              <tr>
                <th className="text-left">Item</th>
                <th className="text-right">Qty</th>
                <th className="text-right">Total</th>
              </tr>
            </thead>
            <tbody>
              {displayItems.map((item, idx) => (
                <tr key={idx}>
                  <td className="text-left">
                    <div className="font-bold">{item.display_name}</div>
                    {item.display_mods?.map((m, i) => (
                      <div
                        key={i}
                        className="receipt-mod">
                        +{m}
                      </div>
                    ))}
                  </td>
                  <td className="text-right">{item.quantity}</td>
                  <td className="text-right">
                    {formatMoney(
                      (item.final_price || item.price || 0) * item.quantity
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="receipt-divider"></div>

          <div className="receipt-totals">
            <div className="total-row">
              <span>Subtotal</span>
              <span>
                $
                {formatMoney(
                  order.total_price || order.total_amount || order.total
                )}
              </span>
            </div>
            {order.payment_method && (
              <div className="total-row text-[10px] italic">
                <span>
                  Method: {String(order.payment_method).toUpperCase()}
                </span>
              </div>
            )}
            <div className="total-row grand-total">
              <span>TOTAL</span>
              <span>
                $
                {formatMoney(
                  order.total_price || order.total_amount || order.total
                )}
              </span>
            </div>
          </div>

          <div className="receipt-footer">
            <p>Thank you for your visit!</p>
            <p className="powered-by">BEEPOS SYSTEM</p>
          </div>
        </div>
      )}

      <style>{`
        .printable-document {
          font-family: 'Courier New', Courier, monospace;
          color: #000;
          background: #fff;
          width: 72mm;
          margin: 0 auto;
          padding: 4mm;
          position: relative;
        }

        .void-watermark {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%) rotate(-45deg);
          font-size: 32px;
          color: rgba(255, 0, 0, 0.3);
          border: 4px solid rgba(255, 0, 0, 0.3);
          padding: 10px;
          z-index: 10;
          pointer-events: none;
          white-space: nowrap;
        }

        .kitchen-header h1 { font-size: 52px; text-align: center; margin: 0; border-bottom: 2px solid #000; line-height: 1; }
        .kitchen-header h1.text-xl { font-size: 28px; }
        .order-meta { display: flex; justify-content: space-between; font-weight: bold; font-size: 12px; margin-top: 4px; }
        .kitchen-item { display: flex; font-size: 20px; font-weight: bold; padding: 8px 0; border-bottom: 1px solid #000; }
        .qty { margin-right: 12px; }
        .mod { display: block; font-size: 14px; font-weight: normal; margin-left: 8px; }
        .item-note { display: block; font-size: 12px; margin-top: 2px; font-style: italic; background: #eee; }

        .restaurant-name { font-size: 18px; text-align: center; text-transform: uppercase; margin: 0; font-weight: 900; }
        .receipt-subtext { text-align: center; font-size: 11px; margin: 1px 0; }
        .receipt-divider { border-top: 1px dashed #000; margin: 8px 0; }
        .receipt-table { width: 100%; font-size: 12px; border-collapse: collapse; }
        .receipt-table th { border-bottom: 1px solid #000; padding-bottom: 4px; }
        .receipt-mod { font-size: 10px; font-style: italic; margin-left: 4px; }
        .total-row { display: flex; justify-content: space-between; padding: 1px 0; }
        .grand-total { font-size: 20px; font-weight: bold; border-top: 2px solid #000; margin-top: 4px; padding-top: 4px; }
        .receipt-footer { text-align: center; margin-top: 20px; font-size: 11px; }
        .powered-by { font-size: 8px; color: #888; margin-top: 8px; }

        @media print {
          body * { visibility: hidden; }
          .printable-document, .printable-document * { visibility: visible; }
          .printable-document { position: absolute; left: 0; top: 0; width: 72mm; }
        }
      `}</style>
    </div>
  );
};

export default PrintableOrderDocument;
