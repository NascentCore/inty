const $ = (s) => document.querySelector(s);

const chatBox = $("#chat-box");
const form = $("#chat-form");
const input = $("#utterance");
const ctxInput = $("#context");
const stateInput = $("#character-state");
const img = $("#emotion-image");
const label = $("#emotion-label");

function appendMessage(role, text) {
  const item = document.createElement("div");
  item.className = `msg ${role}`;
  item.textContent = text;
  chatBox.appendChild(item);
  chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendMessage(e) {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;

  appendMessage("user", text);
  input.value = "";

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        utterance: text,
        context: ctxInput.value || undefined,
        character_state: stateInput.value || undefined,
      }),
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    appendMessage("assistant", data.assistant);
    if (data.image_url) {
      img.src = data.image_url;
    }
    label.textContent = data.emotion || "";
  } catch (err) {
    appendMessage("assistant", `[错误] ${err.message}`);
  }
}

form.addEventListener("submit", sendMessage);

// 初始占位
label.textContent = "Neutral";
