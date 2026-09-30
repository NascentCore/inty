/**
 * Mock CoderPad communication interview simulator.
 * Generated entirely by Cursor agent.
 */

const SCENARIO_PATHS = ["scenarios/lru-cache.json"];

const els = {
  scenarioSelect: document.getElementById("mcp-scenario-select"),
  startBtn: document.getElementById("mcp-start-btn"),
  nextBtn: document.getElementById("mcp-next-btn"),
  micBtn: document.getElementById("mcp-mic-btn"),
  resetBtn: document.getElementById("mcp-reset-btn"),
  autoAdvance: document.getElementById("mcp-auto-advance"),
  stepLabel: document.getElementById("mcp-step-label"),
  typingIndicator: document.getElementById("mcp-typing-indicator"),
  narration: document.getElementById("mcp-narration"),
  yourTurn: document.getElementById("mcp-your-turn"),
  uncleHook: document.getElementById("mcp-uncle-hook"),
  micStatus: document.getElementById("mcp-mic-status"),
  interim: document.getElementById("mcp-interim"),
  transcript: document.getElementById("mcp-transcript"),
  corners: document.getElementById("mcp-corners"),
  editorHost: document.getElementById("mcp-editor-host"),
};

/** @type {CodeMirror.Editor} */
let editor = null;
/** @type {any} */
let scenario = null;
let stepIndex = -1;
let fullCode = "";
let roundActive = false;
let autoAdvanceTimer = null;
/** @type {SpeechRecognition | null} */
let recognition = null;
let micLive = false;

function assertEditor() {
  if (editor !== null) {
    return;
  }
  editor = CodeMirror(els.editorHost, {
    value: "",
    mode: "text/x-java",
    theme: "default",
    lineNumbers: true,
    readOnly: true,
    viewportMargin: Infinity,
  });
}

async function loadScenarios() {
  const scenarios = await Promise.all(
    SCENARIO_PATHS.map(async (path) => {
      const response = await fetch(path);
      if (!response.ok) {
        throw new Error(`Failed to load ${path}`);
      }
      return response.json();
    }),
  );
  els.scenarioSelect.replaceChildren(
    ...scenarios.map((item) => {
      const option = document.createElement("option");
      option.value = item.id;
      option.textContent = item.title;
      option.dataset.path = SCENARIO_PATHS[scenarios.indexOf(item)];
      return option;
    }),
  );
  return scenarios;
}

function renderCorners(items) {
  els.corners.replaceChildren(
    ...items.map((text) => {
      const li = document.createElement("li");
      li.textContent = text;
      return li;
    }),
  );
}

function setStepLabel() {
  const total = scenario ? scenario.steps.length : 0;
  const current = stepIndex >= 0 ? stepIndex + 1 : 0;
  els.stepLabel.textContent = `Step ${current} / ${total}`;
}

function clearAutoAdvance() {
  if (autoAdvanceTimer !== null) {
    window.clearTimeout(autoAdvanceTimer);
    autoAdvanceTimer = null;
  }
}

function scheduleAutoAdvance() {
  clearAutoAdvance();
  if (!roundActive || !els.autoAdvance.checked) {
    return;
  }
  autoAdvanceTimer = window.setTimeout(() => {
    if (roundActive && stepIndex < scenario.steps.length - 1) {
      advanceStep();
    }
  }, 90000);
}

async function typeCodeAddition(addition) {
  els.typingIndicator.hidden = false;
  const chunkSize = 28;
  let typed = "";
  for (let offset = 0; offset < addition.length; offset += chunkSize) {
    typed += addition.slice(offset, offset + chunkSize);
    editor.setValue(fullCode + typed);
    editor.setCursor(editor.lineCount(), 0);
    await new Promise((resolve) => window.setTimeout(resolve, 35));
  }
  fullCode += addition;
  editor.setValue(fullCode);
  els.typingIndicator.hidden = true;
}

function applyStep(step) {
  els.narration.textContent = step.narration;
  els.yourTurn.textContent = step.your_turn;
  setStepLabel();
  scheduleAutoAdvance();
}

async function advanceStep() {
  if (!scenario || stepIndex >= scenario.steps.length - 1) {
    els.nextBtn.disabled = true;
    els.narration.textContent =
      "Round complete. Review your transcript and corners, then reset or pick another scenario.";
    els.yourTurn.textContent = "Nice work. In the real screen, you would debrief with the interviewer.";
    clearAutoAdvance();
    roundActive = false;
    stopMic();
    return;
  }

  stepIndex += 1;
  const step = scenario.steps[stepIndex];
  await typeCodeAddition(step.code_addition);
  applyStep(step);

  if (stepIndex >= scenario.steps.length - 1) {
    els.nextBtn.disabled = true;
  }
}

async function startRound() {
  assertEditor();
  const selected = els.scenarioSelect.selectedOptions[0];
  const path = selected.dataset.path;
  const response = await fetch(path);
  scenario = await response.json();

  stepIndex = -1;
  fullCode = "";
  roundActive = true;
  editor.setValue("");
  els.transcript.replaceChildren();
  els.interim.textContent = "";
  els.uncleHook.textContent = scenario.uncle_hook || "";
  renderCorners(scenario.corner_checklist || []);
  els.nextBtn.disabled = false;
  els.micBtn.disabled = false;
  els.startBtn.disabled = true;
  els.scenarioSelect.disabled = true;

  await advanceStep();
}

function resetRound() {
  clearAutoAdvance();
  roundActive = false;
  stepIndex = -1;
  fullCode = "";
  scenario = null;
  stopMic();
  if (editor) {
    editor.setValue("");
  }
  els.narration.textContent =
    "Pick a scenario and start the round. The interviewer will build code step by step; you respond out loud.";
  els.yourTurn.textContent = "Waiting to start...";
  els.uncleHook.textContent = "";
  els.corners.replaceChildren();
  els.transcript.replaceChildren();
  els.interim.textContent = "";
  els.nextBtn.disabled = true;
  els.micBtn.disabled = true;
  els.startBtn.disabled = false;
  els.scenarioSelect.disabled = false;
  setStepLabel();
}

function appendTranscript(text) {
  const li = document.createElement("li");
  const stamp = document.createElement("time");
  stamp.dateTime = new Date().toISOString();
  stamp.textContent = new Date().toLocaleTimeString();
  li.appendChild(stamp);
  li.appendChild(document.createTextNode(text));
  els.transcript.prepend(li);
}

function speechSupported() {
  return "SpeechRecognition" in window || "webkitSpeechRecognition" in window;
}

function buildRecognition() {
  const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;
  const instance = new SpeechRecognitionCtor();
  instance.lang = "en-US";
  instance.continuous = true;
  instance.interimResults = true;

  instance.onstart = () => {
    micLive = true;
    els.micBtn.textContent = "Mic on";
    els.micBtn.classList.add("is-live");
    els.micStatus.textContent = "Listening - speak clearly toward your microphone";
    els.micStatus.classList.add("is-live");
    els.micStatus.classList.remove("is-error");
  };

  instance.onend = () => {
    micLive = false;
    els.micBtn.textContent = "Mic off";
    els.micBtn.classList.remove("is-live");
    if (!els.micStatus.classList.contains("is-error")) {
      els.micStatus.textContent = "Microphone idle";
      els.micStatus.classList.remove("is-live");
    }
    if (roundActive && recognition !== null) {
      // Browser may stop recognition after silence; keep channel open during round.
      window.setTimeout(() => {
        if (roundActive && recognition !== null && !micLive) {
          try {
            recognition.start();
          } catch (_error) {
            // ignore restart race
          }
        }
      }, 250);
    }
  };

  instance.onerror = (event) => {
    els.micStatus.textContent = `Microphone error: ${event.error}`;
    els.micStatus.classList.add("is-error");
    els.micStatus.classList.remove("is-live");
  };

  instance.onresult = (event) => {
    let interimLine = "";
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const result = event.results[i];
      const text = result[0].transcript.trim();
      if (!text) {
        continue;
      }
      if (result.isFinal) {
        appendTranscript(text);
        els.interim.textContent = "";
      } else {
        interimLine += `${text} `;
      }
    }
    if (interimLine) {
      els.interim.textContent = interimLine.trim();
    }
  };

  return instance;
}

function startMic() {
  if (!speechSupported()) {
    els.micStatus.textContent =
      "SpeechRecognition not supported. Use Chrome or Edge on localhost.";
    els.micStatus.classList.add("is-error");
    return;
  }
  if (recognition === null) {
    recognition = buildRecognition();
  }
  try {
    recognition.start();
  } catch (_error) {
    // already started
  }
}

function stopMic() {
  if (recognition !== null) {
    recognition.onend = null;
    recognition.stop();
    recognition = null;
  }
  micLive = false;
  els.micBtn.textContent = "Mic off";
  els.micBtn.classList.remove("is-live");
  els.micStatus.textContent = "Microphone idle";
  els.micStatus.classList.remove("is-live", "is-error");
}

function toggleMic() {
  if (micLive) {
    stopMic();
    return;
  }
  startMic();
}

function wireEvents() {
  els.startBtn.addEventListener("click", () => {
    startRound().catch((error) => {
      els.micStatus.textContent = String(error);
      els.micStatus.classList.add("is-error");
    });
  });
  els.nextBtn.addEventListener("click", () => {
    advanceStep().catch((error) => {
      els.micStatus.textContent = String(error);
      els.micStatus.classList.add("is-error");
    });
  });
  els.micBtn.addEventListener("click", toggleMic);
  els.resetBtn.addEventListener("click", resetRound);
}

async function boot() {
  assertEditor();
  setStepLabel();
  wireEvents();
  await loadScenarios();
}

boot().catch((error) => {
  els.micStatus.textContent = String(error);
  els.micStatus.classList.add("is-error");
});
