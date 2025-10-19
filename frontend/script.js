const chatButton = document.getElementById("chat-button");
const chatbox = document.getElementById("chatbox");
const messagesDiv = document.getElementById("messages");
const input = document.getElementById("user-input");
const sendBtn = document.getElementById("send");

chatButton.addEventListener("click", () => {
  chatbox.classList.toggle("hidden");
});

sendBtn.addEventListener("click", sendMessage);
input.addEventListener("keypress", (e) => {
  if (e.key === "Enter") sendMessage();
});

async function sendMessage() {
  const message = input.value.trim();
  if (!message) return;

  addMessage("user", message);
  input.value = "";

  addMessage("bot", "Typing...");

  try {
    // Use same-origin so the script works whether served by Flask or a static server
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      const text = await response.text().catch(() => "");
      console.error("Server error:", response.status, text);
      document.querySelectorAll(".bot").forEach(el => el.remove());
      addMessage("bot", "⚠️ Server error. Please try again.");
      return;
    }

    const data = await response.json();
    // Remove the temporary "Typing..." bubbles and show the real reply
    document.querySelectorAll(".bot").forEach(el => el.remove());
    addMessage("bot", data.reply || "(No reply)");
  } catch (err) {
    console.error("Network error:", err);
    document.querySelectorAll(".bot").forEach(el => el.remove());
    addMessage("bot", "⚠️ Error connecting to server.");
  }
}

function addMessage(sender, text) {
  const msg = document.createElement("div");
  msg.className = sender;
  msg.textContent = text;
  messagesDiv.appendChild(msg);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}
