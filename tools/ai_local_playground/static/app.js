/* CREATED_BY_AGENT */

const state = {
  models: [],
  activeTab: "text",
};

function $(id) {
  return document.getElementById(id);
}

function setHealthLine(text, kind) {
  const el = $("health-line");
  el.textContent = text;
  el.className = "playground__health";
  if (kind === "ok") {
    el.classList.add("playground__health--ok");
  } else if (kind === "warn") {
    el.classList.add("playground__health--warn");
  }
}

function fillSelect(selectEl, modality) {
  selectEl.innerHTML = "";
  const list = state.models.filter((m) => m.modality === modality);
  for (const m of list) {
    const opt = document.createElement("option");
    opt.value = m.id_on_provider;
    opt.textContent = `${m.nickname} (${m.id_on_provider})`;
    opt.dataset.notes = m.notes || "";
    selectEl.appendChild(opt);
  }
}

function switchTab(tab) {
  state.activeTab = tab;
  for (const btn of document.querySelectorAll(".playground__tab")) {
    const on = btn.dataset.tab === tab;
    btn.classList.toggle("playground__tab--active", on);
    btn.setAttribute("aria-selected", on ? "true" : "false");
  }
  $("panel-text").classList.toggle("playground__panel--active", tab === "text");
  $("panel-text").hidden = tab !== "text";
  $("panel-image").classList.toggle("playground__panel--active", tab === "image");
  $("panel-image").hidden = tab !== "image";
}

function parseRefUrls(raw) {
  return raw
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
}

function renderImageGallery(images) {
  const gallery = $("image-gallery");
  gallery.innerHTML = "";
  for (const img of images) {
    const src = img.data_url || img.url;
    if (!src) {
      continue;
    }
    const el = document.createElement("img");
    el.className = "playground__thumb";
    el.src = src;
    el.alt = "generated";
    gallery.appendChild(el);
  }
}

async function loadCatalog() {
  const [modelsRes, healthRes] = await Promise.all([
    fetch("/api/models"),
    fetch("/api/health"),
  ]);
  const modelsJson = await modelsRes.json();
  const healthJson = await healthRes.json();
  state.models = modelsJson.models || [];
  fillSelect($("text-model"), "text");
  fillSelect($("image-model"), "image");
  updateImageNotes();
  const parts = [`config: ${healthJson.config_path}`];
  if (!healthJson.openrouter_key_set) {
    parts.push("OPENROUTER_API_KEY missing");
  }
  if (!healthJson.fal_key_set) {
    parts.push("FAL_KEY missing (fal image)");
  }
  const kind =
    healthJson.openrouter_key_set && healthJson.fal_key_set ? "ok" : "warn";
  setHealthLine(parts.join(" · "), kind);
}

function updateImageNotes() {
  const sel = $("image-model");
  const opt = sel.options[sel.selectedIndex];
  $("image-model-notes").textContent = opt ? opt.dataset.notes || "" : "";
}

async function runText() {
  const out = $("text-output");
  const btn = $("text-run");
  btn.disabled = true;
  out.classList.remove("playground__output--error");
  out.textContent = "Running…";
  try {
    const res = await fetch("/api/text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model_id: $("text-model").value,
        user_message: $("text-user").value,
        system_message: $("text-system").value,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || res.statusText);
    }
    out.textContent = data.content || "(empty)";
    const meta = {
      model: data.model,
      elapsed_ms: data.elapsed_ms,
      usage: data.usage,
    };
    out.textContent += `\n\n---\n${JSON.stringify(meta, null, 2)}`;
  } catch (err) {
    out.classList.add("playground__output--error");
    out.textContent = String(err.message || err);
  } finally {
    btn.disabled = false;
  }
}

async function runImage() {
  const out = $("image-output");
  const btn = $("image-run");
  btn.disabled = true;
  out.classList.remove("playground__output--error");
  out.textContent = "Generating…";
  $("image-gallery").innerHTML = "";
  try {
    const res = await fetch("/api/image", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model_id: $("image-model").value,
        prompt: $("image-prompt").value,
        reference_image_urls: parseRefUrls($("image-refs").value),
        system_instruction: $("image-system").value,
        num_images: Number($("image-count").value) || 1,
        input_fidelity: $("image-fidelity").value,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      const detail =
        typeof data.detail === "string"
          ? data.detail
          : JSON.stringify(data.detail);
      throw new Error(detail || res.statusText);
    }
    out.textContent = JSON.stringify(data, null, 2);
    renderImageGallery(data.images || []);
  } catch (err) {
    out.classList.add("playground__output--error");
    out.textContent = String(err.message || err);
  } finally {
    btn.disabled = false;
  }
}

function init() {
  for (const btn of document.querySelectorAll(".playground__tab")) {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  }
  $("text-run").addEventListener("click", runText);
  $("image-run").addEventListener("click", runImage);
  $("image-model").addEventListener("change", updateImageNotes);
  loadCatalog().catch((err) => {
    setHealthLine(`Failed to load: ${err}`, "warn");
  });
}

init();
