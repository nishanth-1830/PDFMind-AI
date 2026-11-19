const API = "/api";
const $ = (id) => document.getElementById(id);

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

// Each browser gets its own random ID (this replaces login)
let sessionId = localStorage.getItem("pdfmind_session");
if (!sessionId) {
  sessionId = (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random())
    .replace(/[^a-zA-Z0-9]/g, "");
  localStorage.setItem("pdfmind_session", sessionId);
}

let docs = [];
const selected = new Set();

async function api(path, options) {
  let res;
  try {
    res = await fetch(API + path, options);
  } catch (e) {
    throw new Error("Cannot reach the server. Is uvicorn running?");
  }
  let data = {};
  try { data = await res.json(); } catch (e) {}
  if (!res.ok) {
    throw new Error(data.detail || `Server error ${res.status}. Check the terminal.`);
  }
  return data;
}

function postJSON(path, body) {
  return api(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

function chosenIds() {
  return selected.size ? Array.from(selected) : null;
}

/* ---------- Tabs ---------- */
document.querySelectorAll(".tab").forEach((btn) => {
  btn.onclick = () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    $(btn.dataset.tab).classList.add("active");
  };
});

/* ---------- Documents ---------- */
async function loadDocs() {
  docs = await api(`/documents?session_id=${sessionId}`);
  for (const id of Array.from(selected)) {
    if (!docs.find((d) => d.doc_id === id)) selected.delete(id);
  }
  renderDocs();
}

function renderDocs() {
  const list = $("docList");
  list.innerHTML = "";
  if (!docs.length) {
    list.appendChild(el("li", "hint", "No documents yet."));
    return;
  }
  docs.forEach((d) => {
    const li = el("li");
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = selected.has(d.doc_id);
    cb.onchange = () => (cb.checked ? selected.add(d.doc_id) : selected.delete(d.doc_id));
    const name = el("span", "name", d.filename);
    name.title = d.filename;
    const del = el("button", "del", "×");
    del.title = "Delete";
    del.onclick = async () => {
      await api(`/documents/${d.doc_id}?session_id=${sessionId}`, { method: "DELETE" });
      loadDocs();
    };
    li.append(cb, name, del);
    list.appendChild(li);
  });
}

$("fileInput").onchange = async (e) => {
  const msg = $("uploadMsg");
  for (const file of e.target.files) {
    msg.textContent = `Processing ${file.name}... please wait`;
    const form = new FormData();
    form.append("session_id", sessionId);
    form.append("file", file);
    try {
      await api("/upload", { method: "POST", body: form });
      msg.textContent = `Uploaded ${file.name}`;
    } catch (err) {
      msg.textContent = `Error: ${err.message}`;
    }
  }
  e.target.value = "";
  loadDocs();
};

/* ---------- Chat ---------- */
let chatLog = [];
try { chatLog = JSON.parse(localStorage.getItem("pdfmind_chat") || "[]"); } catch (e) {}

function addBubble(role, text, sources) {
  const empty = document.querySelector(".empty");
  if (empty) empty.remove();
  const b = el("div", `bubble ${role}`, text);
  if (sources && sources.length) {
    const s = el("div", "sources", "Sources: ");
    sources.forEach((x) => s.appendChild(el("span", null, `${x.filename}, page ${x.page}`)));
    b.appendChild(s);
  }
  $("messages").appendChild(b);
  $("messages").scrollTop = $("messages").scrollHeight;
  return b;
}

function saveChat() {
  localStorage.setItem("pdfmind_chat", JSON.stringify(chatLog.slice(-40)));
}

async function sendChat() {
  const input = $("question");
  const q = input.value.trim();
  if (!q) return;
  input.value = "";
  addBubble("user", q);
  chatLog.push({ role: "user", text: q });
  $("sendBtn").disabled = true;
  const wait = addBubble("bot", "Thinking...");
  try {
    const data = await postJSON("/chat", {
      session_id: sessionId, question: q, doc_ids: chosenIds(),
    });
    wait.remove();
    addBubble("bot", data.answer, data.sources);
    chatLog.push({ role: "bot", text: data.answer, sources: data.sources });
  } catch (err) {
    wait.remove();
    addBubble("bot", "Error: " + err.message);
  }
  saveChat();
  $("sendBtn").disabled = false;
}

$("sendBtn").onclick = sendChat;
$("question").onkeydown = (e) => { if (e.key === "Enter") sendChat(); };

if (chatLog.length) {
  chatLog.forEach((m) => addBubble(m.role, m.text, m.sources));
} else {
  $("messages").appendChild(el("p", "empty", "Upload a PDF, then ask your first question."));
}

/* ---------- Summary ---------- */
$("summaryBtn").onclick = async () => {
  const box = $("summaryBox");
  box.className = "box loading";
  box.textContent = "Generating summary...";
  try {
    const data = await postJSON("/summary", { session_id: sessionId, doc_ids: chosenIds() });
    box.className = "box";
    box.textContent = data.summary;
  } catch (err) {
    box.className = "box";
    box.textContent = "Error: " + err.message;
  }
};

/* ---------- Quiz ---------- */
function loadHistory() {
  let h = [];
  try { h = JSON.parse(localStorage.getItem("pdfmind_scores") || "[]"); } catch (e) {}
  const ul = $("history");
  ul.innerHTML = "";
  if (!h.length) ul.appendChild(el("li", null, "No quizzes taken yet."));
  h.slice(-6).reverse().forEach((x) => ul.appendChild(el("li", null, `${x.date}: ${x.score}/${x.total}`)));
}

function saveScore(score, total) {
  let h = [];
  try { h = JSON.parse(localStorage.getItem("pdfmind_scores") || "[]"); } catch (e) {}
  h.push({ date: new Date().toLocaleDateString(), score, total });
  localStorage.setItem("pdfmind_scores", JSON.stringify(h));
  loadHistory();
}

function renderQuiz(questions) {
  const box = $("quizBox");
  box.innerHTML = "";
  let score = 0, answered = 0;
  questions.forEach((q, qi) => {
    const card = el("div", "card");
    card.appendChild(el("h4", null, `${qi + 1}. ${q.question}`));
    const opts = el("div");
    q.options.forEach((o, oi) => {
      const b = el("button", "opt", o);
      b.onclick = () => {
        if (card.dataset.done) return;
        card.dataset.done = "1";
        answered++;
        if (oi === q.answer) { b.classList.add("right"); score++; }
        else { b.classList.add("wrong"); opts.children[q.answer].classList.add("right"); }
        if (q.explanation) card.appendChild(el("p", "expl", q.explanation));
        if (answered === questions.length) {
          box.appendChild(el("div", "card score", `Your score: ${score} / ${questions.length}`));
          saveScore(score, questions.length);
        }
      };
      opts.appendChild(b);
    });
    card.appendChild(opts);
    box.appendChild(card);
  });
}

$("quizBtn").onclick = async () => {
  const box = $("quizBox");
  box.innerHTML = "";
  box.appendChild(el("p", "loading", "Generating quiz..."));
  try {
    const data = await postJSON("/quiz", { session_id: sessionId, doc_ids: chosenIds() });
    renderQuiz(data.questions);
  } catch (err) {
    box.innerHTML = "";
    box.appendChild(el("div", "box", "Error: " + err.message));
  }
};

/* ---------- Flashcards ---------- */
$("cardsBtn").onclick = async () => {
  const box = $("cardsBox");
  box.innerHTML = "";
  box.appendChild(el("p", "loading", "Generating flashcards..."));
  try {
    const data = await postJSON("/flashcards", { session_id: sessionId, doc_ids: chosenIds() });
    box.innerHTML = "";
    data.cards.forEach((c) => {
      const card = el("div", "flash", c.front);
      let flipped = false;
      card.onclick = () => {
        flipped = !flipped;
        card.textContent = flipped ? c.back : c.front;
        card.classList.toggle("back", flipped);
      };
      box.appendChild(card);
    });
  } catch (err) {
    box.innerHTML = "";
    box.appendChild(el("div", "box", "Error: " + err.message));
  }
};

/* ---------- Start ---------- */
loadHistory();
loadDocs();
$("clearBtn").onclick = () => {
  chatLog = [];
  localStorage.removeItem("pdfmind_chat");
  $("messages").innerHTML = "";
  $("messages").appendChild(el("p", "empty", "Upload a PDF, then ask your first question."));
};