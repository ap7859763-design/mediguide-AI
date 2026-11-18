const navLinks = document.querySelectorAll(".nav-link[data-tab]");
const featureCards = document.querySelectorAll(".feature-card[data-tab]");
const sections = document.querySelectorAll(".page-section");
const pageTitle = document.querySelector("#pageTitle");

const titles = {
  overviewSection: "Overview",
  chatSection: "AI Assistant",
  diseaseSection: "Disease Library",
  faqSection: "FAQ Center"
};

function showTab(tabId) {
  sections.forEach(section => {
    section.classList.toggle("active", section.id === tabId);
  });

  navLinks.forEach(link => {
    link.classList.toggle("active", link.dataset.tab === tabId);
  });

  pageTitle.textContent = titles[tabId] || "MediGuide";
}

navLinks.forEach(link => {
  link.addEventListener("click", () => showTab(link.dataset.tab));
});

featureCards.forEach(card => {
  card.addEventListener("click", () => showTab(card.dataset.tab));
});

const themeToggle = document.querySelector("#themeToggle");

if (localStorage.getItem("mediguide-theme") === "dark") {
  document.body.classList.add("dark-mode");
}

themeToggle.addEventListener("click", () => {
  document.body.classList.toggle("dark-mode");

  localStorage.setItem(
    "mediguide-theme",
    document.body.classList.contains("dark-mode") ? "dark" : "light"
  );
});

const diseaseList = document.querySelector("#diseaseList");
const searchDisease = document.querySelector("#searchDisease");
let allDiseases = [];

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  })[char]);
}

function renderDiseases(items) {
  if (!items.length) {
    diseaseList.innerHTML = '<p class="muted">No matching records found.</p>';
    return;
  }

  diseaseList.innerHTML = items.map(disease => `
    <article class="disease-card">
      <div class="disease-card-top">
        <span class="category-chip">${escapeHTML(disease.category || "General")}</span>
        <span class="disease-symbol">♡</span>
      </div>
      <h3>${escapeHTML(disease.name)}</h3>
      <p>${escapeHTML(disease.description || "No introduction available.")}</p>
      <details>
        <summary>View educational details</summary>
        <div class="detail-content">
          <b>Possible symptoms</b>
          <p>${escapeHTML(disease.symptoms || "Not available")}</p>
          <b>Possible causes</b>
          <p>${escapeHTML(disease.causes || "Not available")}</p>
          <b>Prevention</b>
          <p>${escapeHTML(disease.prevention || "Not available")}</p>
          <b>General care</b>
          <p>${escapeHTML(disease.care || "Not available")}</p>
          <button class="soft-button ask-about" data-name="${escapeHTML(disease.name)}">
            Ask AI about this topic
          </button>
        </div>
      </details>
    </article>
  `).join("");

  document.querySelectorAll(".ask-about").forEach(button => {
    button.addEventListener("click", () => {
      showTab("chatSection");
      document.querySelector("#userInput").value =
        `Explain ${button.dataset.name} in simple language for educational purposes.`;
      document.querySelector("#userInput").focus();
    });
  });
}

async function loadDiseases() {
  try {
    const response = await fetch("/api/diseases");
    if (!response.ok) throw new Error("Could not load disease records.");

    allDiseases = await response.json();
    renderDiseases(allDiseases);
  } catch (error) {
    diseaseList.innerHTML = `<p class="muted">${escapeHTML(error.message)}</p>`;
  }
}

searchDisease.addEventListener("input", () => {
  const query = searchDisease.value.toLowerCase().trim();

  const filtered = allDiseases.filter(disease =>
    [
      disease.name,
      disease.category,
      disease.description,
      disease.symptoms
    ].some(value => String(value || "").toLowerCase().includes(query))
  );

  renderDiseases(filtered);
});

loadDiseases();

const faqList = document.querySelector("#faqList");

async function loadFaqs() {
  try {
    const response = await fetch("/api/faqs");
    if (!response.ok) throw new Error("Could not load FAQs.");

    const faqs = await response.json();

    faqList.innerHTML = faqs.length
      ? faqs.map(faq => `
          <details class="faq-item">
            <summary>${escapeHTML(faq.question)}</summary>
            <p>${escapeHTML(faq.answer)}</p>
            <small>${escapeHTML(faq.category || "General")}</small>
          </details>
        `).join("")
      : '<p class="muted">No FAQs available.</p>';
  } catch (error) {
    faqList.innerHTML = `<p class="muted">${escapeHTML(error.message)}</p>`;
  }
}

loadFaqs();

const chatForm = document.querySelector("#chatForm");
const userInput = document.querySelector("#userInput");
const chatBox = document.querySelector("#chatBox");
const sendBtn = document.querySelector("#sendBtn");
const language = document.querySelector("#language");
const autoSpeak = document.querySelector("#autoSpeak");

let lastAnswer = "";

function addMessage(text, type, source = "") {
  const message = document.createElement("div");
  message.className = type === "user" ? "user-message" : "bot-message";

  const heading = document.createElement("b");
  heading.textContent = type === "user" ? "You" : "MediGuide AI";

  const paragraph = document.createElement("p");
  paragraph.textContent = text;

  message.append(heading, paragraph);

  if (source) {
    const small = document.createElement("small");
    small.className = "message-source";
    small.textContent = `Source: ${source}`;
    message.append(small);
  }

  chatBox.append(message);
  chatBox.scrollTop = chatBox.scrollHeight;
}

chatForm.addEventListener("submit", async event => {
  event.preventDefault();

  const message = userInput.value.trim();
  if (!message) return;

  addMessage(message, "user");
  userInput.value = "";
  sendBtn.disabled = true;
  sendBtn.textContent = "Thinking...";

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        message,
        language: language.value
      })
    });

    const data = await response.json();

    if (!response.ok && !data.reply) {
      throw new Error(data.error || "Unable to get a response.");
    }

    lastAnswer = data.reply || "No response received.";
    addMessage(lastAnswer, "bot", data.source || "");

    if (autoSpeak.checked) {
      speakText(lastAnswer);
    }
  } catch (error) {
    addMessage(error.message, "bot");
  } finally {
    sendBtn.disabled = false;
    sendBtn.innerHTML = 'Send <span>➤</span>';
  }
});

function speakText(text) {
  if (!("speechSynthesis" in window)) {
    document.querySelector("#voiceStatus").textContent =
      "Speech output is not supported in this browser.";
    return;
  }

  window.speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = language.value;
  utterance.rate = 0.95;

  utterance.onstart = () => {
    document.querySelector("#voiceStatus").textContent = "Speaking...";
  };

  utterance.onend = () => {
    document.querySelector("#voiceStatus").textContent = "Ready";
  };

  window.speechSynthesis.speak(utterance);
}

document.querySelector("#speakLast").addEventListener("click", () => {
  if (lastAnswer) speakText(lastAnswer);
});

document.querySelector("#stopVoice").addEventListener("click", () => {
  if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
  document.querySelector("#voiceStatus").textContent = "Voice stopped";
});

const micBtn = document.querySelector("#micBtn");
const SpeechRecognition =
  window.SpeechRecognition || window.webkitSpeechRecognition;

if (SpeechRecognition) {
  const recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;

  micBtn.addEventListener("click", () => {
    recognition.lang = language.value;
    recognition.start();
    document.querySelector("#voiceStatus").textContent = "Listening...";
  });

  recognition.onresult = event => {
    userInput.value = event.results[0][0].transcript;
    document.querySelector("#voiceStatus").textContent = "Voice captured";
    userInput.focus();
  };

  recognition.onerror = () => {
    document.querySelector("#voiceStatus").textContent =
      "Voice input error. You can type instead.";
  };

  recognition.onend = () => {
    if (document.querySelector("#voiceStatus").textContent === "Listening...") {
      document.querySelector("#voiceStatus").textContent = "Ready";
    }
  };
} else {
  micBtn.disabled = true;
  micBtn.title = "Speech recognition is not supported in this browser.";
  document.querySelector("#voiceStatus").textContent =
    "Voice input not supported in this browser";
}
