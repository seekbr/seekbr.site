async function loadPartial(id, url) {
  const el = document.getElementById(id);
  if (!el) return;

  const res = await fetch(url);
  if (!res.ok) return;

  el.innerHTML = await res.text();
}

loadPartial("site-header", "/assets/partials/header.html");