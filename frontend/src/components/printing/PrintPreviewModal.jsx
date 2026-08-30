import React from "react";

const PrintableOrderDocument = ({ order, type = "receipt" }) => {
  if (!order) return null;

  // 1. DYNAMIC BRANDING
  const userData = JSON.parse(localStorage.getItem("user") || "{}");
  const restaurantName =
    order.restaurant_name || userData.restaurant_name || "BEEPOS RESTAURANT";

  const isKitchen = type === "kitchen" || type === "bar";
  const rawItems = order.items || order.order_items || [];

  // 2. ITEM GROUPING LOGIC
  // Combines identical items (same product + same modifiers) into a single line with increased quantity
  const groupedItems = rawItems.reduce((acc, item) => {
    const productName = item.product?.name || item.name;
    const modifierString = JSON.stringify(item.modifiers || []);
    const key = `${productName}-${modifierString}`;

    if (!acc[key]) {
      acc[key] = { ...item, display_name: productName };
    } else {
      acc[key].quantity = (acc[key].quantity || 0) + (item.quantity || 1);
    }
    return acc;
  }, {});

  const displayItems = Object.values(groupedItems);

  // 3. TABLE / IDENTIFIER LOGIC
  // Handles Dine-In (T1, T2) and Take-Out (Customer Name or T/O)
  let tableDisplay = "T/O";
  if (order.table_number || order.table_name) {
    const val = String(order.table_number || order.table_name);
    tableDisplay = val.startsWith("T") ? val : `T${val}`;
  } else if (order.customer_name && order.customer_name !== "Guest") {
    tableDisplay = order.customer_name.toUpperCase();
  }

  const formatMoney = (val) => Number(val || 0).toFixed(2);

  return (
    <div className="printable-document">
      {isKitchen ? (
        /* KITCHEN TICKET */
        <div className="kitchen-ticket">
          <div className="kitchen-header">
            <h1 className={tableDisplay.length > 4 ? "text-xl" : ""}>
              {tableDisplay}
            </h1>
            <div className="order-meta">
              <span>#{order.display_id || order.id}</span>
              <span>
                {new Date().toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
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
                  {item.modifiers?.map((m, i) => (
                    <span
                      key={i}
                      className="mod">
                      • {m.name}
                    </span>
                  ))}
                  {item.notes && (
                    <span className="item-note">** {item.notes}</span>
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
              Order #{order.display_id || order.id}
            </p>
            <p className="receipt-subtext">{new Date().toLocaleString()}</p>
            <p className="receipt-subtext font-bold">Table: {tableDisplay}</p>
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
              {displayItems.map((item, idx) => (
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
                    {formatMoney(
                      (item.final_price || item.price) * item.quantity
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
              <span>${formatMoney(order.total_price || order.total)}</span>
            </div>
            <div className="total-row grand-total">
              <span>TOTAL</span>
              <span>${formatMoney(order.total_price || order.total)}</span>
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

        .kitchen-header h1 {
          font-size: 64px;
          text-align: center;
          margin: 0;
          border-bottom: 2px solid #000;
          line-height: 1.1;
        }
        
        .kitchen-header h1.text-xl {
          font-size: 32px; /* For longer customer names */
        }

        .order-meta {
          display: flex;
          justify-content: space-between;
          font-weight: bold;
          font-size: 14px;
          margin-top: 5px;
        }

        .kitchen-item {
          display: flex;
          font-size: 22px;
          font-weight: bold;
          padding: 10px 0;
          border-bottom: 1px solid #ccc;
        }

        .qty { margin-right: 15px; }
        
        .mod {
          display: block;
          font-size: 16px;
          font-weight: normal;
          margin-left: 10px;
        }

        .item-note {
          display: block;
          font-size: 14px;
          color: #444;
          margin-top: 4px;
        }

        .restaurant-name {
          font-size: 20px;
          text-align: center;
          text-transform: uppercase;
          margin: 0;
        }

        .receipt-subtext {
          text-align: center;
          font-size: 12px;
          margin: 2px 0;
        }

        .receipt-divider {
          border-top: 1px dashed #000;
          margin: 10px 0;
        }

        .receipt-table {
          width: 100%;
          font-size: 14px;
        }

        .receipt-mod {
          font-size: 11px;
          font-style: italic;
          margin-left: 5px;
        }

        .grand-total {
          font-size: 20px;
          font-weight: bold;
          border-top: 2px solid #000;
          margin-top: 5px;
          padding-top: 5px;
        }

        .receipt-footer {
          text-align: center;
          margin-top: 30px;
        }

        .powered-by {
          font-size: 8px;
          color: #888;
          margin-top: 10px;
        }

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
