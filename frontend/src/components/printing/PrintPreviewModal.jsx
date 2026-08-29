import React from "react";

const PrintableOrderDocument = ({ order, type = "receipt" }) => {
  if (!order) return null;

  const isKitchen = type === "kitchen" || type === "bar";
  const items = order.items || order.order_items || [];

  // Logic for Table Name: T1, T2 or T/O (Take Out)
  const tableDisplay = order.table_name
    ? `T${order.table_name.replace(/\D/g, "") || order.table_name}`
    : "T/O";

  const formatMoney = (val) => Number(val || 0).toFixed(2);

  return (
    <div className="printable-document">
      {isKitchen ? (
        /* KITCHEN TICKET: Bold Table ID and Items Only */
        <div className="kitchen-ticket">
          <div className="kitchen-header">
            <h1>{tableDisplay}</h1>
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
            {items.map((item, idx) => (
              <div
                key={idx}
                className="kitchen-item">
                <span className="qty">{item.quantity}x</span>
                <div className="details">
                  <span className="name">
                    {item.product?.name || item.name}
                  </span>
                  {item.modifiers?.map((m, i) => (
                    <span
                      key={i}
                      className="mod">
                      • {m.name}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        /* CUSTOMER RECEIPT: Restaurant Name, Items, Prices, Total */
        <div className="customer-receipt">
          <div className="receipt-header">
            <h2 className="restaurant-name">
              {order.restaurant_name || "BEEPOS RESTAURANT"}
            </h2>
            <p className="receipt-subtext">
              Order #{order.display_id || order.id}
            </p>
            <p className="receipt-subtext">{new Date().toLocaleString()}</p>
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
              {items.map((item, idx) => (
                <tr key={idx}>
                  <td className="text-left">
                    {item.product?.name || item.name}
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
                    {formatMoney(item.final_price)}
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
          </div>
        </div>
      )}

      <style>{`
        .printable-document {
          font-family: 'Courier New', Courier, monospace;
          color: #000;
          background: #fff;
          width: 300px; /* Standard 80mm width */
          margin: 0 auto;
          padding: 10px;
        }

        /* Kitchen Styles */
        .kitchen-header {
          text-align: center;
          border-bottom: 2px solid #000;
          padding-bottom: 10px;
          margin-bottom: 10px;
        }
        .kitchen-header h1 {
          font-size: 64px;
          margin: 0;
          line-height: 1;
        }
        .order-meta {
          display: flex;
          justify-content: space-between;
          font-size: 14px;
          font-weight: bold;
        }
        .kitchen-item {
          display: flex;
          align-items: flex-start;
          gap: 10px;
          padding: 8px 0;
          border-bottom: 1px solid #eee;
          font-size: 20px;
          font-weight: bold;
        }
        .kitchen-item .mod {
          display: block;
          font-size: 14px;
          font-weight: normal;
          margin-left: 10px;
        }

        /* Receipt Styles */
        .receipt-header {
          text-align: center;
          margin-bottom: 10px;
        }
        .restaurant-name {
          font-size: 18px;
          font-weight: bold;
          text-transform: uppercase;
          margin: 0;
        }
        .receipt-subtext {
          font-size: 11px;
          margin: 2px 0;
        }
        .receipt-divider {
          border-top: 1px dashed #000;
          margin: 10px 0;
        }
        .receipt-table {
          width: 100%;
          font-size: 12px;
          border-collapse: collapse;
        }
        .receipt-table th {
          border-bottom: 1px solid #000;
          padding-bottom: 5px;
        }
        .receipt-table td {
          padding: 5px 0;
          vertical-align: top;
        }
        .receipt-mod {
          font-size: 10px;
          color: #555;
          font-style: italic;
        }
        .text-left { text-align: left; }
        .text-right { text-align: right; }
        
        .receipt-totals {
          margin-top: 10px;
        }
        .total-row {
          display: flex;
          justify-content: space-between;
          font-size: 13px;
          margin-bottom: 3px;
        }
        .grand-total {
          font-size: 18px;
          font-weight: bold;
          border-top: 1px solid #000;
          padding-top: 5px;
        }
        .receipt-footer {
          text-align: center;
          margin-top: 20px;
          font-size: 12px;
        }

        @media print {
          body * {
            visibility: hidden;
          }
          .printable-document, .printable-document * {
            visibility: visible;
          }
          .printable-document {
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
          }
        }
      `}</style>
    </div>
  );
};

export default PrintableOrderDocument;
