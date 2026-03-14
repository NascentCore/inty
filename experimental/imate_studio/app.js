const repositoryCharacters = [
  {
    id: "repo-lumi",
    name: "Lumi Vega",
    archetype: "Visionary producer",
    desire: "Create truthful art",
    secret: "Signed a predatory deal",
    source: "repository"
  },
  {
    id: "repo-kai",
    name: "Kai Mercer",
    archetype: "Ex-stunt engineer",
    desire: "Redeem past failure",
    secret: "Caused a major on-set accident",
    source: "repository"
  },
  {
    id: "repo-sora",
    name: "Sora Lin",
    archetype: "Data driven critic",
    desire: "Prove stories can heal",
    secret: "Ghostwrites viral drama recaps",
    source: "repository"
  },
  {
    id: "repo-mira",
    name: "Mira Holt",
    archetype: "Mentor strategist",
    desire: "Protect new creators",
    secret: "Leaked one rival's pitch years ago",
    source: "repository"
  }
];

const plotChecklistTemplate = [
  { id: "inciting", label: "Inciting incident appears in first 60 seconds", done: false },
  { id: "stakes", label: "Stakes escalate before midpoint", done: false },
  { id: "reversal", label: "Relationship reversal changes alliance", done: false },
  { id: "twist", label: "Twist redefines objective around minute 4", done: false },
  { id: "payoff", label: "Emotional callback lands near ending", done: false },
  { id: "clear_end", label: "Ending resolves main character desire", done: false }
];

const scenes = Array.from({ length: 12 }, (_, idx) => {
  const start = idx * 30;
  const end = start + 30;
  return {
    id: idx + 1,
    title: `Scene ${idx + 1}`,
    start,
    end,
    note: idx === 0 ? "Opening setup and world tone." : "Open beat.",
    actions: []
  };
});

const state = {
  drafts: [],
  cast: {
    lead: "",
    partner: "",
    rival: "",
    mentor: ""
  },
  currentTime: 0,
  intentPrompt: "",
  intentSummary: "No intent scaffold yet. Describe your film idea to get agentic setup.",
  commandResult: "No command executed yet.",
  plotChecklist: structuredClone(plotChecklistTemplate),
  logs: ["Studio initialized: start building your 6-minute story."]
};

function main() {
  bindEvents();
  renderAll();
}

function bindEvents() {
  document.getElementById("dify-form").addEventListener("submit", onGenerateDraft);
  document.getElementById("scaffold-intent").addEventListener("click", onScaffoldIntent);
  document.getElementById("smart-cast").addEventListener("click", onSmartCast);
  document.getElementById("run-ai-command").addEventListener("click", onRunAiCommand);
  document.getElementById("rewind").addEventListener("click", () => shiftTime(-15));
  document.getElementById("advance").addEventListener("click", () => shiftTime(15));
  document.getElementById("prev-scene").addEventListener("click", () => jumpScene(-1));
  document.getElementById("next-scene").addEventListener("click", () => jumpScene(1));
  document.getElementById("timeline").addEventListener("input", (event) => setTime(Number(event.target.value)));
  document.getElementById("perform-action").addEventListener("click", onPerformAction);
  document.getElementById("analyze-gaps").addEventListener("click", onAnalyzeGaps);
  document.getElementById("auto-fill-gaps").addEventListener("click", onAutoFillGaps);

  ["lead", "partner", "rival", "mentor"].forEach((slot) => {
    document.getElementById(`cast-${slot}`).addEventListener("change", (event) => {
      state.cast[slot] = event.target.value;
      pushLog(`Cast updated: ${slot} -> ${event.target.value || "unassigned"}`);
      renderAll();
    });
  });
}

function onScaffoldIntent() {
  const input = document.getElementById("intent-prompt").value.trim();
  if (!input) {
    state.commandResult = "Please provide a story intent prompt first.";
    renderAll();
    return;
  }

  state.intentPrompt = input;
  state.intentSummary = buildIntentSummary(input);

  scenes[0].note = "Hook: invite audience into the world you personally love.";
  scenes[3].note = "Connection beat: audience sees why this story matters to you.";
  scenes[7].note = "Reversal: trust breaks and raises stakes for everyone.";
  scenes[11].note = "Payoff: shared joy lands and audience feels included.";

  pushLog("Intent scaffold generated from natural language prompt.");
  state.commandResult = "Scaffold complete: timeline now reflects your emotional intent.";
  renderAll();
}

function onSmartCast() {
  if (!state.cast.lead) {
    state.cast.lead = repositoryCharacters[0].name;
  }
  if (!state.cast.partner) {
    state.cast.partner = repositoryCharacters[1].name;
  }
  if (!state.cast.rival) {
    state.cast.rival = repositoryCharacters[2].name;
  }
  if (!state.cast.mentor) {
    state.cast.mentor = repositoryCharacters[3].name;
  }

  pushLog("Smart cast assigned from character repository.");
  state.commandResult = "Smart cast complete: four roles are now assigned.";
  renderAll();
}

function onRunAiCommand() {
  const input = document.getElementById("ai-command").value.trim();
  if (!input) {
    state.commandResult = "Type a command first.";
    renderAll();
    return;
  }

  const normalized = input.toLowerCase();
  let handled = false;
  let resultText = "Command understood, but no action matched.";

  const sceneMatch = normalized.match(/scene\s+(\d+)/);
  if (normalized.includes("rewind")) {
    if (sceneMatch) {
      const targetScene = clampSceneIndex(Number(sceneMatch[1]) - 1);
      setTime(scenes[targetScene].start);
      resultText = `Moved to scene ${targetScene + 1}.`;
    } else {
      shiftTime(-30);
      resultText = "Rewound by 30 seconds.";
    }
    handled = true;
  } else if (normalized.includes("advance")) {
    if (sceneMatch) {
      const targetScene = clampSceneIndex(Number(sceneMatch[1]) - 1);
      setTime(scenes[targetScene].start);
      resultText = `Moved to scene ${targetScene + 1}.`;
    } else {
      shiftTime(30);
      resultText = "Advanced by 30 seconds.";
    }
    handled = true;
  } else if (normalized.includes("betray")) {
    const target = sceneMatch ? clampSceneIndex(Number(sceneMatch[1]) - 1) : currentSceneIndex();
    scenes[target].note = "Rival betrayal flips trust dynamics.";
    scenes[target].actions.push({
      roleSlot: "rival",
      roleName: state.cast.rival || "(unassigned rival)",
      action: "Trigger relationship reversal",
      improv: "I chose survival over loyalty."
    });
    markChecklistItemDone("reversal");
    resultText = `Added betrayal reversal in scene ${target + 1}.`;
    handled = true;
  } else if (normalized.includes("mark payoff")) {
    markChecklistItemDone("payoff");
    resultText = "Marked payoff beat as done.";
    handled = true;
  } else if (normalized.includes("smart cast")) {
    onSmartCast();
    resultText = "Smart cast command applied.";
    handled = true;
  }

  if (!handled) {
    resultText = "Try commands like: rewind to scene 3, make rival betray in scene 8, mark payoff done.";
  }

  state.commandResult = resultText;
  pushLog(`AI command: "${input}" -> ${resultText}`);
  document.getElementById("ai-command").value = "";
  renderAll();
}

function buildIntentSummary(prompt) {
  return [
    "You loved this story and want others to enjoy it too.",
    `Core prompt: "${prompt}"`,
    "Studio AI plan: hook fast, deepen connection at scene 4, break trust near scene 8, end with shared emotional payoff."
  ].join(" ");
}

function onGenerateDraft(event) {
  event.preventDefault();
  const name = document.getElementById("dify-name").value.trim();
  const archetype = document.getElementById("dify-archetype").value.trim();
  const desire = document.getElementById("dify-desire").value.trim();
  const secret = document.getElementById("dify-secret").value.trim();

  const id = `draft-${Date.now()}`;
  state.drafts.unshift({
    id,
    name,
    archetype,
    desire,
    secret,
    source: "dify-draft"
  });

  pushLog(`Dify draft generated: ${name} (${archetype}).`);
  event.target.reset();
  renderAll();
}

function onPerformAction() {
  const roleSlot = document.getElementById("active-role").value;
  const roleName = state.cast[roleSlot] || `(unassigned ${roleSlot})`;
  const action = document.getElementById("scene-action").value;
  const improv = document.getElementById("improv-line").value.trim();
  const scene = currentScene();

  scene.actions.push({ roleSlot, roleName, action, improv });
  scene.note = `${roleName}: ${action}${improv ? ` | "${improv}"` : ""}`;

  updatePlotCoverageFromAction(action);
  pushLog(`Role-play: ${roleName} performed "${action}" in ${scene.title}.`);
  document.getElementById("improv-line").value = "";
  renderAll();
}

function updatePlotCoverageFromAction(action) {
  const mapping = {
    "Raise stakes with hard choice": "stakes",
    "Trigger relationship reversal": "reversal",
    "Twist mission objective": "twist",
    "Deliver emotional callback": "payoff",
    "Plant setup for climax": "clear_end",
    "Reveal hidden motive": "inciting"
  };

  const checklistId = mapping[action];
  const item = state.plotChecklist.find((entry) => entry.id === checklistId);
  if (item) {
    item.done = true;
  }
}

function onAnalyzeGaps() {
  const gaps = calculateGaps();
  pushLog(`Gap analysis completed: ${gaps.length} issue(s) found.`);
  renderGapList(gaps);
}

function onAutoFillGaps() {
  const gaps = calculateGaps();
  gaps.forEach((gap) => {
    if (gap.type === "plot") {
      const item = state.plotChecklist.find((entry) => entry.id === gap.id);
      if (item) {
        item.done = true;
      }
    }
    if (gap.type === "cast" && !state.cast.mentor) {
      state.cast.mentor = "Mira Holt";
      document.getElementById("cast-mentor").value = "Mira Holt";
    }
  });
  pushLog(`Auto-fill applied for ${gaps.length} issue(s).`);
  state.commandResult = "Missing ideas auto-filled to keep momentum for AI-native creators.";
  renderAll();
  renderGapList(calculateGaps());
}

function calculateGaps() {
  const gaps = [];
  const castValues = Object.values(state.cast).filter(Boolean);
  if (castValues.length < 3) {
    gaps.push({
      type: "cast",
      severity: "bad",
      id: "cast-coverage",
      text: "At least 3 cast roles should be assigned for rich interaction."
    });
  }

  state.plotChecklist.forEach((item) => {
    if (!item.done) {
      gaps.push({
        type: "plot",
        severity: "warn",
        id: item.id,
        text: `Plot beat missing: ${item.label}`
      });
    }
  });

  const activeScenes = scenes.filter((scene) => scene.actions.length > 0).length;
  if (activeScenes < 4) {
    gaps.push({
      type: "timeline",
      severity: "warn",
      id: "scene-density",
      text: "Role-play across at least 4 scenes to avoid flat pacing."
    });
  }

  return gaps;
}

function shiftTime(deltaSeconds) {
  setTime(state.currentTime + deltaSeconds);
}

function setTime(nextSeconds) {
  const bounded = Math.max(0, Math.min(360, nextSeconds));
  state.currentTime = bounded;
  renderTimelineOnly();
}

function jumpScene(direction) {
  const idx = currentSceneIndex();
  const nextIdx = Math.max(0, Math.min(scenes.length - 1, idx + direction));
  setTime(scenes[nextIdx].start);
}

function currentSceneIndex() {
  return Math.min(Math.floor(state.currentTime / 30), scenes.length - 1);
}

function currentScene() {
  return scenes[currentSceneIndex()];
}

function allCharacters() {
  return [...repositoryCharacters, ...state.drafts];
}

function renderAll() {
  renderRepository();
  renderDrafts();
  renderCastSelectors();
  renderIntentSummary();
  renderTimelineOnly();
  renderPlotChecklist();
  renderGapList(calculateGaps());
  renderCommandResult();
  renderEventLog();
}

function renderRepository() {
  const root = document.getElementById("repository");
  root.innerHTML = repositoryCharacters.map((character) => {
    return `
      <article class="card">
        <strong>${character.name}</strong>
        <div class="meta">${character.archetype}</div>
        <div class="meta">Desire: ${character.desire}</div>
      </article>
    `;
  }).join("");
}

function renderDrafts() {
  const root = document.getElementById("dify-drafts");
  if (state.drafts.length === 0) {
    root.innerHTML = `<div class="card"><span class="meta">No generated drafts yet.</span></div>`;
    return;
  }

  root.innerHTML = state.drafts.map((character) => {
    return `
      <article class="card">
        <strong>${character.name}</strong>
        <div class="meta">${character.archetype}</div>
        <div class="meta">Desire: ${character.desire}</div>
        <div class="meta">Secret: ${character.secret}</div>
      </article>
    `;
  }).join("");
}

function renderCastSelectors() {
  const choices = ["", ...allCharacters().map((character) => character.name)];
  ["lead", "partner", "rival", "mentor"].forEach((slot) => {
    const select = document.getElementById(`cast-${slot}`);
    const previous = state.cast[slot];
    select.innerHTML = choices.map((choice) => {
      const label = choice || "(unassigned)";
      return `<option value="${choice}">${label}</option>`;
    }).join("");
    select.value = previous;
  });
}

function renderTimelineOnly() {
  const timeline = document.getElementById("timeline");
  timeline.value = String(state.currentTime);

  document.getElementById("current-time-label").textContent = formatTime(state.currentTime);
  const scene = currentScene();
  document.getElementById("scene-focus").textContent = `Focused scene: ${scene.title} (${formatTime(scene.start)}-${formatTime(scene.end)})`;

  const sceneRoot = document.getElementById("scenes");
  sceneRoot.innerHTML = scenes.map((entry, idx) => {
    const activeClass = idx === currentSceneIndex() ? "scene active" : "scene";
    const lastAction = entry.actions.length > 0 ? entry.actions[entry.actions.length - 1].action : "No role action yet";
    return `
      <article class="${activeClass}">
        <strong>${entry.title}</strong>
        <div class="stamp">${formatTime(entry.start)}-${formatTime(entry.end)}</div>
        <p class="meta">${entry.note}</p>
        <p class="meta">Latest: ${lastAction}</p>
      </article>
    `;
  }).join("");
}

function renderPlotChecklist() {
  const root = document.getElementById("plot-list");
  root.innerHTML = state.plotChecklist.map((item) => {
    const klass = item.done ? "ok" : "warn";
    const marker = item.done ? "PASS" : "MISSING";
    return `<li class="${klass}">${marker}: ${item.label}</li>`;
  }).join("");
}

function renderGapList(gaps) {
  const root = document.getElementById("gap-list");
  if (gaps.length === 0) {
    root.innerHTML = `<li class="ok">All major gaps covered. Ready for shot planning.</li>`;
    return;
  }

  root.innerHTML = gaps.map((gap) => {
    return `<li class="${gap.severity}">${gap.text}</li>`;
  }).join("");
}

function renderIntentSummary() {
  const root = document.getElementById("intent-summary");
  root.innerHTML = `
    <strong>Intent summary</strong>
    <div class="meta">${state.intentSummary}</div>
  `;
}

function renderCommandResult() {
  const root = document.getElementById("command-result");
  root.innerHTML = `
    <strong>Command result</strong>
    <div class="meta">${state.commandResult}</div>
  `;
}

function markChecklistItemDone(id) {
  const item = state.plotChecklist.find((entry) => entry.id === id);
  if (item) {
    item.done = true;
  }
}

function clampSceneIndex(idx) {
  return Math.max(0, Math.min(scenes.length - 1, idx));
}

function renderEventLog() {
  const root = document.getElementById("event-log");
  root.textContent = state.logs.slice(-40).join("\n");
  root.scrollTop = root.scrollHeight;
}

function pushLog(line) {
  state.logs.push(`[${formatTime(state.currentTime)}] ${line}`);
}

function formatTime(totalSeconds) {
  const mm = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
  const ss = String(totalSeconds % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

main();
