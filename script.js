const chatButton = document.getElementById("chat-button");
const chatbox = document.getElementById("chatbox");
const messagesDiv = document.getElementById("messages");
const userInput = document.getElementById("user-input");
const sendButton = document.getElementById("send");
const resetButton = document.getElementById("reset");

// Show/hide chatbox
chatButton.addEventListener("click", () => {
  chatbox.classList.toggle("hidden");
  userInput.focus();
});

// Helper: create a message div and return the element
function appendMessage(text, sender, risk = "low") {
  const msg = document.createElement("div");
  msg.className = sender;

  // Color-code bot messages by risk
  if (sender === "bot") {
    if (risk === "high") msg.style.backgroundColor = "#ff4d4d";
    else if (risk === "medium") msg.style.backgroundColor = "#ffa500";
    else msg.style.backgroundColor = "#e5e5ea";
  } else {
    msg.style.backgroundColor = "#0078ff";
    msg.style.color = "#fff";
    msg.style.marginLeft = "auto";
  }

  msg.textContent = text; // \n preserved by CSS pre-wrap
  messagesDiv.appendChild(msg);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
  return msg;
}

// Typing indicator we can replace later
function showTyping(risk = "low") {
  const el = appendMessage("typing…", "bot", risk);
  let dots = 0;
  const id = setInterval(() => {
    dots = (dots + 1) % 4;
    el.textContent = "typing" + ".".repeat(dots);
  }, 400);
  el._typingInterval = id;
  return el;
}
function stopTyping(el) {
  if (el && el._typingInterval) {
    clearInterval(el._typingInterval);
    delete el._typingInterval;
  }
}

// Type out a reply (or just swap text for long replies)
async function typeMessage(sender, text, risk = "low", reuseEl = null) {
  const msg = reuseEl || appendMessage("", sender, risk);

  if (text.length > 2000) {
    msg.textContent = text;
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    return;
  }
  let i = 0;
  while (i < text.length) {
    msg.textContent += text[i++];
    await new Promise(r => setTimeout(r, 20));
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }
}

// Send message to Flask backend
async function sendMessage() {
  const userMessage = userInput.value.trim();
  if (!userMessage) return;

  appendMessage(userMessage, "user");
  userInput.value = "";

  const typingEl = showTyping();

  // 10s client-side timeout so UI never hangs
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), 10000);

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: userMessage }),
      signal: controller.signal,
    });
    clearTimeout(t);

    if (!res.ok) {
      const body = await res.text().catch(() => "");
      console.error("Server error:", res.status, body);
      stopTyping(typingEl);
      typingEl.textContent = "Server error. Please try again.";
      return;
    }

    let data;
    try {
      data = await res.json();
    } catch (e) {
      const raw = await res.text().catch(() => "");
      console.error("Bad JSON:", e, raw);
      stopTyping(typingEl);
      typingEl.textContent = "Unexpected server response.";
      return;
    }

    stopTyping(typingEl);
    typingEl.textContent = ""; // reuse bubble
    await typeMessage("bot", data.reply || "Oops, something went wrong!", data.risk || "low", typingEl);

  } catch (err) {
    clearTimeout(t);
    console.error("Network error:", err);
    stopTyping(typingEl);
    typingEl.textContent = "Error connecting to server.";
  }
}

// Click to send
sendButton.addEventListener("click", sendMessage);

// Press Enter to send
userInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    sendMessage();
  }
});

// Reset chat (clear UI; DB handled server-side)
if (resetButton) {
  resetButton.addEventListener("click", async () => {
    try {
      const res = await fetch("/reset", { method: "POST" });
      await res.json();
      messagesDiv.innerHTML = "";
      userInput.focus();
    } catch (err) {
      console.error(err);
      appendMessage("Error on reset", "bot");
    }
  });
}
