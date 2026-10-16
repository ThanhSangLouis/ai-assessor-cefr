(() => {
  const root = document.getElementById("admin-billing-summary");
  if (!root) return;

  const addRow = (list, label, value) => {
    const row = document.createElement("div");
    const term = document.createElement("strong");
    const detail = document.createElement("span");
    term.textContent = label;
    detail.textContent = value == null || value === "" ? "Chưa có dữ liệu" : String(value);
    row.append(term, detail);
    list.append(row);
  };

  const readJson = async (url) => {
    const response = await fetch(url, { credentials: "same-origin", cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP_${response.status}`);
    return response.json();
  };

  const load = async () => {
    try {
      const [billing, orders] = await Promise.all([
        readJson("/api/v1/admin/billing"),
        readJson("/api/v1/admin/billing/orders"),
      ]);
      const list = document.createElement("dl");
      list.className = "admin-summary-list";
      const overview = billing.overview || {};
      const license = billing.license || {};
      const gateways = billing.gateways || {};
      const entitlement = overview.entitlement || {};
      const usage = overview.usage || {};
      addRow(list, "Gói hiện hành", entitlement.plan_code);
      addRow(list, "Giới hạn người học", usage.student_limit);
      addRow(list, "License", license.plan_code || `${license.license_count || 0} license`);
      addRow(list, "Cổng sandbox", Object.entries(gateways).map(([name, value]) => `${name}: ${value.mode || (value.enabled ? "available" : "disabled")}`).join(" · "));
      addRow(list, "Đơn hàng", Array.isArray(orders.items) ? orders.items.length : 0);
      root.replaceChildren(list);
      root.setAttribute("aria-busy", "false");
    } catch (_error) {
      const message = document.createElement("p");
      message.className = "notice";
      message.setAttribute("role", "status");
      message.textContent = "Chưa đọc được trạng thái billing. Contract/API hiện tại vẫn là nguồn dữ liệu; thao tác tạo đơn tiếp tục bị khóa trên giao diện này.";
      root.replaceChildren(message);
      root.setAttribute("aria-busy", "false");
    }
  };

  load();
})();
