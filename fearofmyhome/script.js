async function loadModalContent(modalEl, url) {
  const body = modalEl.querySelector(".modal-body");
  if (body.dataset.loaded === "true") return;

  try {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error("Erro ao carregar " + url);
    body.innerHTML = await res.text();
    body.dataset.loaded = "true";
  } catch (err) {
    body.innerHTML = "<p>Erro ao carregar conteúdo.</p>";
    console.error(err);
  }
}

function openModal(modalEl, closeBtn, url) {
  return async () => {
    await loadModalContent(modalEl, url);
    modalEl.classList.add("is-open");
    modalEl.setAttribute("aria-hidden", "false");
    document.body.classList.add("modal-open");
    closeBtn?.focus();
  };
}

function closeModal(modalEl, openBtn) {
  modalEl.classList.remove("is-open");
  modalEl.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
  openBtn?.focus();
}

const openSkillsBtn = document.getElementById("openSkills");
const skillsModal = document.getElementById("skillsModal");

openSkillsBtn?.addEventListener("click", async () => {
  await loadModalContent(skillsModal, "modals/skills.html");

  skillsModal.classList.add("is-open");
  skillsModal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
});

// fechar por botão (delegação)
skillsModal.addEventListener("click", (e) => {
  if (e.target.closest("[data-modal-close]")) {
    closeModal(skillsModal, openSkillsBtn);
  }

  // clique fora
  if (e.target === skillsModal) {
    closeModal(skillsModal, openSkillsBtn);
  }
});

const openConceptsBtn = document.getElementById("openConcepts");
const conceptsModal = document.getElementById("conceptsModal");

openConceptsBtn?.addEventListener("click", async () => {
  await loadModalContent(conceptsModal, "modals/concepts.html");

  conceptsModal.classList.add("is-open");
  conceptsModal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
});

conceptsModal.addEventListener("click", (e) => {
  if (e.target.closest("[data-modal-close]")) {
    closeModal(conceptsModal, openConceptsBtn);
  }

  if (e.target === conceptsModal) {
    closeModal(conceptsModal, openConceptsBtn);
  }
});
