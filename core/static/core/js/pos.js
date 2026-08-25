// POS Dashboard
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

    if (!categoryContainer || !itemContainer || !orderList || !orderTotal || !submitOrderBtn) {
        console.warn("POS elements not found on this page.");
        return;
    }

    // =========================================================================
    // STATE
    // =========================================================================
    let cart = [];
    let menuItems = [];

    // =========================================================================
    // API ENDPOINTS
    // =========================================================================
    const CATEGORIES_API = "/categories/";
    const MENU_API = "/products/";
    const PLACE_ORDER_API = "/pos-save-order/";

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
        let html = `<button class="category-btn active" data-id="all">All</button>`;

        list.forEach(cat => {
            html += `
                <button class="category-btn" data-id="${cat.id}">
                    ${cat.name}
                </button>
            `;
        });

        categoryContainer.innerHTML = html;
    }

    function renderMenuItems(items) {
        if (!items.length) {
            itemContainer.innerHTML =
                `<p class="text-slate-500 text-center py-6">No items available.</p>`;
            return;
        }

        let html = "";

        items.forEach(i => {
            html += `
               <div
                 class="bg-white rounded-lg shadow p-4 hover:shadow-lg cursor-pointer transition"
                 data-id="${i.id}">
                 <h3 class="text-lg font-bold text-slate-800">${i.name}</h3>
                 <p class="text-slate-600 mt-1">$${Number(i.price).toFixed(2)}</p>
               </div>
            `;
        });

        itemContainer.innerHTML = html;
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
        if (!cart.length) {
            orderList.innerHTML =
                `<p class="text-center text-slate-500 py-4">No items added yet.</p>`;
            submitOrderBtn.disabled = true;
            orderTotal.textContent = "0.00";
            return;
        }

        let total = 0;
        let html = "";

        cart.forEach(item => {
            const lineTotal = item.price * item.qty;
            total += lineTotal;

            html += `
                <div class="flex justify-between py-2 border-b">
                    <div>
                        <p class="font-semibold">${item.name}</p>
                        <p class="text-xs text-slate-500">$${item.price.toFixed(2)}</p>
                    </div>
                    <div class="flex gap-2 items-center">
                        <button class="px-2 py-1 bg-slate-200 rounded change-qty" data-id="${item.variantId}" data-act="dec">-</button>
                        <span>${item.qty}</span>
                        <button class="px-2 py-1 bg-slate-200 rounded change-qty" data-id="${item.variantId}" data-act="inc">+</button>
                        <button class="text-red-500 delete-item" data-id="${item.variantId}">&times;</button>
                    </div>
                </div>
            `;
        });

        orderList.innerHTML = html;
        orderTotal.textContent = total.toFixed(2);
        submitOrderBtn.disabled = false;
    }

    function addToCart(id) {
        const product = menuItems.find(m => String(m.id) === String(id));
        if (!product) return;

        const existing = cart.find(i => String(i.variantId) === String(id));

        if (existing) {
            existing.qty++;
        } else {
            cart.push({
                variantId: product.id,   // ✅ UUID safe
                name: product.name,
                price: Number(product.price),
                qty: 1,
                category: product.category_name || "General"
            });
        }

        updateOrderList();
    }

    // =========================================================================
    // PRINTING
    // =========================================================================
    function openPrintWindow(html) {
        const w = window.open("", "_blank", "width=380,height=600");
        if (!w) return;
        w.document.write(html);
        w.document.close();
        w.focus();
        w.print();
    }

    function printKitchenTicket(items, orderId) {
        let content = `<html><body style="font-family:monospace;">`;
        content += `<h3>Kitchen Order #${orderId}</h3><hr>`;

        items.forEach(item => {
            content += `<p><strong>${item.qty}x</strong> ${item.name}</p>`;
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
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrftoken,
                },
                body: JSON.stringify({
                    items: cart.map(i => ({
                        variantId: i.variantId,
                        qty: i.qty
                    }))
                }),
            });

            const data = await res.json();

            if (data.success) {
                printKitchenTicket(cart, data.order_id);
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

    submitOrderBtn.addEventListener("click", submitOrder);

    // =========================================================================
    // INIT
    // =========================================================================
    async function init() {
        try {
            const [catRes, itemRes] = await Promise.all([
                fetch(CATEGORIES_API, { credentials: "same-origin" }),
                fetch(MENU_API, { credentials: "same-origin" })
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
    categoryContainer.addEventListener("click", e => {
        if (e.target.classList.contains("category-btn")) {
            filterMenu(e.target.dataset.id);
        }
    });

    itemContainer.addEventListener("click", e => {
        const card = e.target.closest("[data-id]");
        if (card) addToCart(card.dataset.id);  // ✅ NO Number()
    });

    orderList.addEventListener("click", e => {
        const id = e.target.dataset.id;  // ✅ UUID string

        if (e.target.classList.contains("change-qty")) {
            const item = cart.find(i => String(i.variantId) === String(id));
            if (!item) return;

            if (e.target.dataset.act === "inc") item.qty++;
            if (e.target.dataset.act === "dec") {
                item.qty--;
                if (item.qty <= 0)
                    cart = cart.filter(i => String(i.variantId) !== String(id));
            }

            updateOrderList();
        }

        if (e.target.classList.contains("delete-item")) {
            cart = cart.filter(i => String(i.variantId) !== String(id));
            updateOrderList();
        }
    });

});