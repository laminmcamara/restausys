console.log("Tables JS Loaded");

document.addEventListener("DOMContentLoaded", function () {

    // ===============================
    // CSRF HELPER
    // ===============================
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

    // ===============================
    // QR REGENERATE
    // ===============================
    document.addEventListener("click", function (e) {
        const btn = e.target.closest(".regenerate-btn");
        if (!btn) return;

        const tableId = btn.dataset.id;

        fetch(`/tables/${tableId}/regenerate-qr/`, {
            method: "POST",
            headers: {
                "X-CSRFToken": csrftoken,
            },
            credentials: "same-origin"
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert(data.error || "Failed to regenerate QR.");
            }
        })
        .catch(err => console.error("QR Error:", err));
    });

});