import React from "react";

const PrintableOrderDocument = ({ order, type = "receipt" }) => {
  if (!order) return null;

  // 1. DYNAMIC NAME LOGIC
  const userData = JSON.parse(localStorage.getItem("user") || "{}");
  const restaurantName =
    order.restaurant_name || userData.restaurant_name || "BEEPOS RESTAURANT";

  const isKitchen = type === "kitchen" || type === "bar";

  // 2. DATA NORMALIZATION (Fixes $0.00 and Invalid Date)
  const rawItems = order.items || order.order_items || [];

  // Use total_amount (standard backend field) or total_price/total as fallbacks
  const orderTotal =
    order.total_amount || order.total_price || order.total || 0;

  // Safe Date Parsing
  const orderDate = order.created_at || order.date;
  const displayDate = orderDate
    ? new Date(orderDate).toLocaleString()
    : new Date().toLocaleString();
  const displayTime = orderDate
    ? new Date(orderDate).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      })
    : new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  // 3. ITEM GROUPING LOGIC
  const groupedItems = rawItems.reduce((acc, item) => {
    const productName =
      item.product_name || item.product?.name || "Unknown Item";
    const modifierString = JSON.stringify(item.modifiers || []);
    const key = `${productName}-${modifierString}`;

    if (!acc[key]) {
      acc[key] = { ...item, display_name: productName };
    } else {
      acc[key].quantity += item.quantity;
    }
    return acc;
  }, {});

  const displayItems = Object.values(groupedItems);

  // Logic for Table Name: T1, T2 or T/O (Take Out)
  const tableDisplay =
    order.table_name || order.table_number
      ? `T${
          String(order.table_name || order.table_number).replace(/\D/g, "") ||
          order.table_name ||
          order.table_number
        }`
      : "T/O";

  const formatMoney = (val) => Number(val || 0).toFixed(2);

  return (
    <div className="printable-document">
      {isKitchen ? (
        /* KITCHEN TICKET */
        <div className="kitchen-ticket">
          <div className="kitchen-header">
            <h1>{tableDisplay}</h1>
            <div className="order-meta">
              <span>#{order.display_id || order.id?.toString().slice(-6)}</span>
              <span>{displayTime}</span>
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
                  {item.modifiers?.map((m, i) => (
                    <span
                      key={i}
                      className="mod">
                      • {m.name}
                    </span>
                  ))}
                  {item.notes && (
                    <span className="item-note">Note: {item.notes}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        /* CUSTOMER RECEIPT */
        <div className="customer-receipt">
          <div className="receipt-header">
            <h2 className="restaurant-name">{restaurantName}</h2>
            <p className="receipt-subtext">
              Order #{order.display_id || order.id?.toString().slice(-6)}
            </p>
            <p className="receipt-subtext">{displayDate}</p>
            <p className="receipt-subtext">Table: {tableDisplay}</p>
          </div>

          <div className="receipt-divider"></div>

          <table className="receipt-table">
            <thead>
              <tr>
                <th className="text-left">Item</th>
                <th className="text-right">Qty</th>
                <th className="text-right">Price</th>
              </tr>
            </thead>
            <tbody>
              {displayItems.map((item, idx) => {
                const itemPrice =
                  item.final_price || item.unit_price || item.price || 0;
                return (
                  <tr key={idx}>
                    <td className="text-left">
                      {item.display_name}
                      {item.modifiers?.map((m, i) => (
                        <div
                          key={i}
                          className="receipt-mod">
                          +{m.name}
                        </div>
                      ))}
                    </td>
                    <td className="text-right">{item.quantity}</td>
                    <td className="text-right">
                      {formatMoney(itemPrice * item.quantity)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          <div className="receipt-divider"></div>

          <div className="receipt-totals">
            <div className="total-row">
              <span>Subtotal</span>
              <span>${formatMoney(orderTotal)}</span>
            </div>
            <div className="total-row grand-total">
              <span>TOTAL</span>
              <span>${formatMoney(orderTotal)}</span>
            </div>
          </div>

          <div className="receipt-footer">
            <p>Thank you for your visit!</p>
            <p className="powered-by">Powered by BEEPOS</p>
          </div>
        </div>
      )}

      <style>{`
        .printable-document {
          font-family: 'Courier New', Courier, monospace;
          color: #000;
          background: #fff;
          width: 300px;
          margin: 0 auto;
          padding: 10px;
        }
        .kitchen-header h1 { font-size: 64px; text-align: center; margin: 0; border-bottom: 2px solid #000; }
        .kitchen-item { display: flex; font-size: 22px; font-weight: bold; padding: 10px 0; border-bottom: 1px solid #ccc; }
        .qty { margin-right: 15px; }
        .mod { display: block; font-size: 16px; font-weight: normal; margin-left: 10px; }
        .item-note { display: block; font-size: 14px; font-style: italic; color: #444; margin-top: 4px; }
        .restaurant-name { font-size: 20px; text-align: center; text-transform: uppercase; margin: 0; }
        .receipt-subtext { text-align: center; font-size: 12px; margin: 2px 0; }
        .receipt-divider { border-top: 1px dashed #000; margin: 10px 0; }
        .receipt-table { width: 100%; font-size: 14px; }
        .total-row { display: flex; justify-content: space-between; font-size: 14px; margin: 2px 0; }
        .grand-total { font-size: 20px; font-weight: bold; border-top: 2px solid #000; margin-top: 5px; padding-top: 5px; }
        .receipt-footer { text-align: center; margin-top: 30px; }
        .powered-by { font-size: 8px; color: #888; margin-top: 10px; }
        .text-left { text-align: left; }
        .text-right { text-align: right; }
        @media print {
          body * { visibility: hidden; }
          .printable-document, .printable-document * { visibility: visible; }
          .printable-document { position: absolute; left: 0; top: 0; width: 100%; }
        }
      `}</style>
    </div>
  );
};

export default PrintableOrderDocument;
