// C:\Users\Administrator\restaurant_management\core\static\core\js\pos_dashboard.js

console.log("POS Dashboard JS Loaded");

document.addEventListener("DOMContentLoaded", function () {

    // =========================================================================
    // DOM SELECTORS
    // =========================================================================
    const categoryContainer = document.getElementById("category-bar");
    const itemContainer = document.getElementById("menu-items-grid");
    const orderList = document.getElementById("order-summary-list");
    const orderTotal = document.getElementById("order-total");
    const submitOrderBtn = document.getElementById("submit-order");

    // =========================================================================
    // STATE
    // =========================================================================
    let cart = [];
    let menuItems = [];

    // =========================================================================
    // API ENDPOINTS
    // =========================================================================
    const CATEGORIES_API = "/api/menu-categories/";
    const MENU_API = "/api/menu-items/";
    const PLACE_ORDER_API = "/api/new-order/";
    // =========================================================================
    // CSRF
    // =========================================================================
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== "") {
            const cookies = document.cookie.split(";");
            for (let cookie of cookies) {
                cookie = cookie.trim();
                if (cookie.startsWith(name + "=")) {
                    cookieValue = decodeURIComponent(cookie.slice(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    const csrftoken = getCookie("csrftoken");

    // =========================================================================
    // MENU RENDERING
    // =========================================================================
    function renderCategories(list) {
        if (!categoryContainer) return;

        categoryContainer.innerHTML = `
            <button class="category-btn active" data-id="all">All</button>
        `;

        list.forEach(cat => {
            categoryContainer.innerHTML += `
                <button class="category-btn" data-id="${cat.id}">
                    ${cat.name}
                </button>
            `;
        });
    }

    function renderMenuItems(items) {
        itemContainer.innerHTML = "";

        if (!items.length) {
            itemContainer.innerHTML =
                `<p class="text-slate-500 text-center py-6">No items available.</p>`;
            return;
        }

        items.forEach(i => {
            itemContainer.innerHTML += `
               <div
                 class="bg-white rounded-lg shadow p-4 hover:shadow-lg cursor-pointer transition"
                 data-id="${i.id}">
                 <h3 class="text-lg font-bold text-slate-800">${i.name}</h3>
                 <p class="text-slate-600 mt-1">$${parseFloat(i.price).toFixed(2)}</p>
               </div>
            `;
        });
    }

    function filterMenu(categoryId) {
        const filtered = categoryId === "all"
            ? menuItems
            : menuItems.filter(i => String(i.category_id) === String(categoryId));

        renderMenuItems(filtered);

        document.querySelectorAll(".category-btn").forEach(btn => {
            btn.classList.toggle("active", btn.dataset.id === categoryId);
        });
    }

    // =========================================================================
    // CART
    // =========================================================================
    function updateOrderList() {
        orderList.innerHTML = "";

        if (!cart.length) {
            orderList.innerHTML =
                `<p class="text-center text-slate-500 py-4">No items added yet.</p>`;
            submitOrderBtn.disabled = true;
            orderTotal.textContent = "0.00";
            return;
        }

        let total = 0;

        cart.forEach(item => {
            const lineTotal = item.price * item.qty;
            total += lineTotal;

            orderList.innerHTML += `
                <div class="flex justify-between py-2 border-b">
                    <div>
                        <p class="font-semibold">${item.name}</p>
                        <p class="text-xs text-slate-500">$${item.price.toFixed(2)}</p>
                    </div>
                    <div class="flex gap-2 items-center">
                        <button class="px-2 py-1 bg-slate-200 rounded change-qty" data-id="${item.id}" data-act="dec">-</button>
                        <span>${item.qty}</span>
                        <button class="px-2 py-1 bg-slate-200 rounded change-qty" data-id="${item.id}" data-act="inc">+</button>
                        <button class="text-red-500 delete-item" data-id="${item.id}">&times;</button>
                    </div>
                </div>
            `;
        });

        orderTotal.textContent = total.toFixed(2);
        submitOrderBtn.disabled = false;
    }

    function addToCart(id) {
        const product = menuItems.find(m => m.id === id);
        if (!product) return;

        const existing = cart.find(i => i.id === id);

        if (existing) {
            existing.qty++;
        } else {
            cart.push({
                id: product.id,
                name: product.name,
                price: parseFloat(product.price),
                qty: 1,
                category: product.category_name || "General"
            });
        }

        updateOrderList();
    }

    // =========================================================================
    // ENTERPRISE PRINT CONFIG
    // =========================================================================
    const PRINT_CONFIG = {
        restaurantName: "My Restaurant",
        address: "123 Main Street",
        phone: "555-123-4567",
        taxRate: 0.08,
        logoUrl: "/static/images/logo.png",
        silentMode: false
    };

    function openPrintWindow(html) {
        const w = window.open("", "_blank", "width=380,height=600");
        if (!w) return;

        w.document.write(html);
        w.document.close();
        w.focus();
        w.print();
    }

    function printCustomerReceipt(items, orderId) {

        let subtotal = 0;
        items.forEach(i => subtotal += i.price * i.qty);

        const tax = subtotal * PRINT_CONFIG.taxRate;
        const total = subtotal + tax;

        let rows = "";
        items.forEach(item => {
            const line = item.price * item.qty;
            rows += `
                <tr>
                    <td>${item.qty}x ${item.name}</td>
                    <td style="text-align:right">$${line.toFixed(2)}</td>
                </tr>
            `;
        });

        const html = `
        <html>
        <head>
            <style>
                body { font-family: monospace; width: 80mm; padding:10px; }
                h2,p { text-align:center; margin:2px 0; }
                hr { border:none; border-top:1px dashed #000; margin:6px 0; }
                table { width:100%; font-size:12px; }
                .right { text-align:right; }
            </style>
        </head>
        <body>

            <h2>${PRINT_CONFIG.restaurantName}</h2>
            <p>${PRINT_CONFIG.address}</p>
            <p>${PRINT_CONFIG.phone}</p>

            <hr>
            <p>Order #${orderId}</p>
            <p>${new Date().toLocaleString()}</p>
            <hr>

            <table>${rows}</table>

            <hr>
            <table>
                <tr>
                    <td>Subtotal</td>
                    <td class="right">$${subtotal.toFixed(2)}</td>
                </tr>
                <tr>
                    <td>Tax (${PRINT_CONFIG.taxRate * 100}%)</td>
                    <td class="right">$${tax.toFixed(2)}</td>
                </tr>
                <tr>
                    <td><strong>TOTAL</strong></td>
                    <td class="right"><strong>$${total.toFixed(2)}</strong></td>
                </tr>
            </table>

            <hr>
            <p>Thank you!</p>

        </body>
        </html>
        `;

        openPrintWindow(html);
    }

    function printKitchenTicket(items, orderId) {

        const grouped = {};
        items.forEach(item => {
            if (!grouped[item.category]) grouped[item.category] = [];
            grouped[item.category].push(item);
        });

        let content = `
        <html>
        <head>
            <style>
                body { font-family: monospace; width:80mm; padding:10px; }
                h2 { text-align:center; }
                hr { border:none; border-top:1px dashed #000; margin:6px 0; }
                .item { font-size:16px; font-weight:bold; margin:4px 0; }
                .category { margin-top:8px; font-weight:bold; }
            </style>
        </head>
        <body>

            <h2>KITCHEN ORDER</h2>
            <p>Order #${orderId}</p>
            <p>${new Date().toLocaleString()}</p>
            <hr>
        `;

        Object.keys(grouped).forEach(cat => {
            content += `<div class="category">${cat}</div>`;
            grouped[cat].forEach(item => {
                content += `<div class="item">${item.qty}x ${item.name}</div>`;
            });
            content += `<hr>`;
        });

        content += `</body></html>`;

        openPrintWindow(content);
    }

    // =========================================================================
    // ORDER SUBMIT
    // =========================================================================
    async function submitOrder() {

        if (!cart.length) return;

        submitOrderBtn.disabled = true;
        submitOrderBtn.innerText = "Processing...";

        try {
            const res = await fetch(PLACE_ORDER_API, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrftoken,
                },
                body: JSON.stringify({
                    items: cart.map(i => ({ id: i.id, qty: i.qty }))
                }),
            });

            const data = await res.json();

            if (data.success) {

                printKitchenTicket(cart, data.order_id);
                printCustomerReceipt(cart, data.order_id);

                cart = [];
                updateOrderList();

            } else {
                alert(data.error || "Order failed.");
            }

        } catch (err) {
            console.error("Checkout error:", err);
        }

        submitOrderBtn.disabled = false;
        submitOrderBtn.innerText = "Submit Order";
    }

    submitOrderBtn?.addEventListener("click", submitOrder);

    // =========================================================================
    // INIT
    // =========================================================================
    async function init() {
        try {
            const [catRes, itemRes] = await Promise.all([
                fetch(CATEGORIES_API),
                fetch(MENU_API)
            ]);

            const categories = await catRes.json();
            menuItems = await itemRes.json();

            renderCategories(categories);
            filterMenu("all");

        } catch (err) {
            console.error("Init error:", err);
        }
    }

    init();

    // =========================================================================
    // EVENTS
    // =========================================================================
    categoryContainer?.addEventListener("click", e => {
        if (e.target.classList.contains("category-btn")) {
            filterMenu(e.target.dataset.id);
        }
    });

    itemContainer?.addEventListener("click", e => {
        const card = e.target.closest("[data-id]");
        if (card) {
            addToCart(parseInt(card.dataset.id));
        }
    });

    orderList?.addEventListener("click", e => {
        const id = parseInt(e.target.dataset.id);

        if (e.target.classList.contains("change-qty")) {
            const act = e.target.dataset.act;
            const item = cart.find(i => i.id === id);
            if (!item) return;

            if (act === "inc") item.qty++;
            if (act === "dec") {
                item.qty--;
                if (item.qty <= 0)
                    cart = cart.filter(i => i.id !== id);
            }
            updateOrderList();
        }

        if (e.target.classList.contains("delete-item")) {
            cart = cart.filter(i => i.id !== id);
            updateOrderList();
        }
    });

});