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
    const response = await fetch("http://localhost:5000/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });

    const data = await response.json();
    document.querySelectorAll(".bot").forEach(el => el.remove());
    addMessage("bot", data.reply);
  } catch (err) {
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
