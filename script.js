async function loadPartial(id, url, callback) {
  const el = document.getElementById(id);
  if (!el) return;

  const res = await fetch(url);
  if (!res.ok) return;

  el.innerHTML = await res.text();

  if (callback) callback();
}

async function fetchDiscordStatus(userId) {
  const res = await fetch(`https://api.lanyard.rest/v1/users/${userId}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Falha ao consultar Lanyard");
  const json = await res.json();

  // online | idle | dnd | offline
  return json?.data?.discord_status || "offline";
}

async function updateProfileStatusDiscord() {
  const statusIcon = document.getElementById("statusIcon");
  const statusText = document.getElementById("statusText");
  if (!statusIcon || !statusText) return;

  try {
    const s = await fetchDiscordStatus("1146906311582294127");

    const map = {
      online: {
        icon: "/assets/icons/online.png",
        text: "Online"
      },
      idle: {
        icon: "/assets/icons/idle.png",
        text: "Ausente"
      },
      dnd: {
        icon: "/assets/icons/dnd.png",
        text: "Não perturbe"
      },
      offline: {
        icon: "/assets/icons/offline.png",
        text: "Offline"
      }
    };

    const data = map[s] || map.offline;

    statusIcon.src = data.icon;
    statusIcon.alt = data.text;
    statusText.textContent = data.text;

  } catch (e) {
    statusIcon.src = "/assets/icons/offline.png";
    statusIcon.alt = "Offline";
    statusText.textContent = "Offline";
    console.error(e);
  }
}

loadPartial("site-header", "/partials/header.html");
loadPartial("site-footer", "/partials/footer.html", () => {
  updateProfileStatusDiscord();
});
setInterval(updateProfileStatusDiscord, 30_000);