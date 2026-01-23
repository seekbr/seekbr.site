async function loadPartial(id, url, callback) {
  const el = document.getElementById(id);
  if (!el) return;

  const res = await fetch(url);
  if (!res.ok) return;

  el.innerHTML = await res.text();

  if (callback) callback();
}

function updateProfileStatus() {
  // ✅ Ano (só se existir)
  const yearEl = document.getElementById("year");
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  // ✅ Status (só se existir)
  const statusDot = document.getElementById("statusDot");
  const statusText = document.getElementById("statusText");
  if (!statusDot || !statusText) return;

  function getBrazilNowParts() {
    const parts = new Intl.DateTimeFormat("pt-BR", {
      timeZone: "America/Sao_Paulo",
      weekday: "short",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false
    }).formatToParts(new Date());

    const map = {};
    for (const p of parts) map[p.type] = p.value;

    return {
      weekday: (map.weekday || "").toLowerCase(),
      hour: Number(map.hour),
      minute: Number(map.minute)
    };
  }

  function isBusinessOpen({ weekday, hour, minute }) {
    const isWeekend =
      weekday.startsWith("sáb") || weekday.startsWith("sab") || weekday.startsWith("dom");
    if (isWeekend) return false;

    const nowMinutes = hour * 60 + minute;
    const start = 12 * 60 + 30;
    const end = 22 * 60;

    return nowMinutes >= start && nowMinutes < end;
  }

  const now = getBrazilNowParts();
  const online = isBusinessOpen(now);

  statusDot.classList.toggle("online", online);
  statusDot.classList.toggle("offline", !online);
  statusText.textContent = online ? "Online" : "Offline";
}

loadPartial("site-header", "/partials/header.html");
loadPartial("site-footer", "/partials/footer.html", () => {
  updateProfileStatus(); // agora o #year EXISTE
});
setInterval(updateProfileStatus, 30_000);
