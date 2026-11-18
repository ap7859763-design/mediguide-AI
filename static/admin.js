const modal = document.querySelector("#editorModal");
const form = document.querySelector("#editorForm");
const fieldsHost = document.querySelector("#editorFields");

let entity = "disease";
let editingId = null;

const diseaseFields = [
  ["name", "Disease name", "text", true],
  ["category", "Category", "text", false],
  ["description", "Introduction", "textarea", true],
  ["symptoms", "Symptoms", "textarea", true],
  ["causes", "Causes", "textarea", false],
  ["prevention", "Prevention", "textarea", false],
  ["care", "General care", "textarea", false]
];

const faqFields = [
  ["question", "Question", "textarea", true],
  ["answer", "Answer", "textarea", true],
  ["category", "Category", "text", false]
];

function openEditor(type, record = null) {
  entity = type;
  editingId = record ? record.id : null;

  document.querySelector("#editorTitle").textContent =
    `${record ? "Edit" : "Add"} ${type}`;

  fieldsHost.replaceChildren();

  (type === "disease" ? diseaseFields : faqFields).forEach(
    ([key, label, kind, required]) => {
      const wrap = document.createElement("label");
      wrap.className = "form-field" + (kind === "textarea" ? " full" : "");
      wrap.textContent = label;

      const input = document.createElement(
        kind === "textarea" ? "textarea" : "input"
      );

      input.name = key;
      input.required = required;
      input.value = record?.[key] || "";

      wrap.append(input);
      fieldsHost.append(wrap);
    }
  );

  modal.classList.remove("hidden");
}

function closeEditor() {
  modal.classList.add("hidden");
}

document.querySelector("#newDisease").addEventListener(
  "click", () => openEditor("disease")
);

document.querySelector("#newFaq").addEventListener(
  "click", () => openEditor("faq")
);

document.querySelector("#closeModal").addEventListener("click", closeEditor);
document.querySelector("#cancelModal").addEventListener("click", closeEditor);

document.querySelectorAll(".edit-disease").forEach(button => {
  button.addEventListener("click", () => {
    openEditor("disease", JSON.parse(button.dataset.record));
  });
});

document.querySelectorAll(".edit-faq").forEach(button => {
  button.addEventListener("click", () => {
    openEditor("faq", JSON.parse(button.dataset.record));
  });
});

async function api(url, method, body) {
  const response = await fetch(url, {
    method,
    headers: {"Content-Type": "application/json"},
    body: body ? JSON.stringify(body) : undefined
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.error || "Request failed");
  }

  return data;
}

form.addEventListener("submit", async event => {
  event.preventDefault();

  const payload = Object.fromEntries(new FormData(form).entries());
  const base = entity === "disease"
    ? "/api/admin/diseases"
    : "/api/admin/faqs";

  try {
    await api(
      editingId ? `${base}/${editingId}` : base,
      editingId ? "PUT" : "POST",
      payload
    );
    location.reload();
  } catch (error) {
    alert(error.message);
  }
});

document.querySelectorAll(".delete-disease").forEach(button => {
  button.addEventListener("click", async () => {
    if (!confirm("Delete this disease record?")) return;

    try {
      await api(`/api/admin/diseases/${button.dataset.id}`, "DELETE");
      location.reload();
    } catch (error) {
      alert(error.message);
    }
  });
});

document.querySelectorAll(".delete-faq").forEach(button => {
  button.addEventListener("click", async () => {
    if (!confirm("Delete this FAQ?")) return;

    try {
      await api(`/api/admin/faqs/${button.dataset.id}`, "DELETE");
      location.reload();
    } catch (error) {
      alert(error.message);
    }
  });
});

document.querySelectorAll(".admin-tab").forEach(button => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".admin-tab").forEach(tab => {
      tab.classList.toggle("active", tab === button);
    });

    document.querySelectorAll(".admin-panel").forEach(panel => {
      panel.classList.toggle("active", panel.id === button.dataset.panel);
    });
  });
});
