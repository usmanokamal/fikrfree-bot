// static/chatbot.js (FikrFree)
(function () {
  const ICONS = {
    copy: '<svg width="16" height="16" viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><rect x="3" y="3" width="13" height="13" rx="2" fill="none" stroke="currentColor" stroke-width="2"/></svg>',
    thumbUp: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M7 11v9a2 2 0 0 1-2 2H3v-9h2a2 2 0 0 1 2-2z" stroke="currentColor" stroke-width="2"/><path d="M7 11l4.5-7.5A2 2 0 0 1 13.2 3h.8a2 2 0 0 1 2 2v6h3.8a2 2 0 0 1 2 2.2l-1 6A2 2 0 0 1 19 21h-8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    thumbDown: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M7 13V4a2 2 0 0 1 2-2h2v9H9a2 2 0 0 1-2 2z" stroke="currentColor" stroke-width="2"/><path d="M7 13l4.5 7.5A2 2 0 0 0 13.2 21h.8a2 2 0 0 0 2-2v-6h3.8a2 2 0 0 0 2-2.2l-1-6A2 2 0 0 0 19 3h-8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
  };
  let currentController = null;
  let sessionId = generateSessionId();
  let currentView = "web";
  let currentMessageElement = null;

  function generateSessionId() {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
      const r = (Math.random() * 16) | 0, v = c === "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  function appendMessage(text, sender, messageId = null) {
    let bubble = $("<div>").addClass("chat-bubble").addClass(sender);

    if (sender === "bot") {
      const messageWrapper = $("<div>").addClass("bot-message-wrapper");
      const contentContainer = $("<div>").addClass("bot-content-container");
      const avatar = $("<div>").addClass("bot-avatar");
      const logo = $("<img>")
        .attr("src", "/static/assets/fikrfree-logo.png")
        .attr("alt", "FikrFree Logo");
      avatar.append(logo);

      let formattedText = formatText(text);
      const messageContent = $("<span>").html(formattedText);
      contentContainer.append(avatar).append(messageContent);
      messageWrapper.append(contentContainer);

      if (messageId) {
        const feedbackButtons = createFeedbackButtons(messageId, window.lastUserMessage, text);
        messageWrapper.append(feedbackButtons);
      }

      bubble.append(messageWrapper);
    } else {
      bubble.text(text);
      window.lastUserMessage = text;
    }

    $("#chat-box").append(bubble);
    $("#chat-box").scrollTop($("#chat-box")[0].scrollHeight);
    return bubble;
  }

  function startTypingAnimation() { $("#robotArea").addClass("robot-thinking"); }
  function stopTypingAnimation() { $("#robotArea").removeClass("robot-thinking"); }

  function disableUI() {
    $("#send-btn").prop("disabled", true);
    $("#user-input").prop("disabled", true);
    $("#mic-btn").prop("disabled", true);
    $("#stop-btn").show();
    startTypingAnimation();
  }
  function enableUI() {
    $("#send-btn").prop("disabled", false);
    $("#user-input").prop("disabled", false);
    $("#mic-btn").prop("disabled", false);
    $("#stop-btn").hide();
    $("#user-input").focus();
    stopTypingAnimation();
  }

  function formatText(text) {
    if (!text) return "";

    // Basic Markdown: bold + headings (keep newlines for list processing)
    let t = String(text)
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/^### (.*$)/gm, "<h3 style='font-size:1.05em;font-weight:700;margin:10px 0 6px;'>$1</h3>")
      .replace(/^## (.*$)/gm, "<h2 style='font-size:1.15em;font-weight:800;margin:12px 0 6px;'>$1</h2>")
      .replace(/^# (.*$)/gm, "<h1 style='font-size:1.25em;font-weight:800;margin:14px 0 8px;'>$1</h1>");

    // Convert consecutive lines starting with "- " into an unordered list
    const lines = t.split(/\n/);
    let html = "";
    let inList = false;
    for (const line of lines) {
      const m = line.match(/^\s*-\s+(.*)/);
      if (m) {
        if (!inList) { html += "<ul style='margin:6px 0 8px 18px;padding:0;'>"; inList = true; }
        html += `<li style='margin:2px 0;'>${m[1]}</li>`;
      } else {
        if (inList) { html += "</ul>"; inList = false; }
        if (line.trim().length) {
          html += `${line}<br>`;
        } else {
          html += "<br>"; // preserve blank lines
        }
      }
    }
    if (inList) html += "</ul>";
    // Simple autolink for URLs
    html = html.replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener">$1<\/a>');
    return html;
  }

  function createBotMessage(messageId) {
    const bubble = $("<div>").addClass("chat-bubble").addClass("bot");
    const messageWrapper = $("<div>").addClass("bot-message-wrapper");

    const contentContainer = $("<div>").addClass("bot-content-container");
    const avatar = $("<div>").addClass("bot-avatar");
    const logo = $("<img>")
      .attr("src", "/static/assets/fikrfree-logo.png")
      .attr("alt", "FikrFree Logo");
    avatar.append(logo);

    const messageContent = $("<span>");
    contentContainer.append(avatar).append(messageContent);
    messageWrapper.append(contentContainer);

    const feedbackContainer = $("<div>").addClass("feedback-container-placeholder");
    messageWrapper.append(feedbackContainer);

    bubble.append(messageWrapper);
    $("#chat-box").append(bubble);
    $("#chat-box").scrollTop($("#chat-box")[0].scrollHeight);

    return { messageContent, feedbackContainer };
  }

  function sendMessage() {
    let responseTimeout = setTimeout(() => {
      if ($("#send-btn").prop("disabled")) {
        if (currentMessageElement) currentMessageElement.html("<em>Error: Response timed out. Please try again.</em>");
        enableUI();
      }
    }, 60000);

    const input = $("#user-input");
    const userMsg = input.val().trim();
    if (!userMsg) return;

    appendMessage(userMsg, "user");
    input.val("");
    disableUI();

    const messageId = Date.now().toString();
    const thinkingBubble = appendMessage("<em>Thinking...</em>", "bot", null);
    let thinkingRemoved = false;
    let botMessageCreated = false;
    let messageContent, feedbackContainer;
    let accumulatedText = "";

    currentController = new AbortController();
    const signal = currentController.signal;

    fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: userMsg, session_id: sessionId }),
      signal,
    })
    .then(async (response) => {
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          if (feedbackContainer) {
            const feedbackButtons = createFeedbackButtons(messageId, userMsg, accumulatedText);
            feedbackContainer.replaceWith(feedbackButtons);
          }
          break;
        }
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.substring(6));
              if (data.type === "content") {
                if (!botMessageCreated) {
                  if (thinkingBubble && !thinkingRemoved) { thinkingBubble.remove(); thinkingRemoved = true; }
                  const botMsg = createBotMessage(messageId);
                  messageContent = botMsg.messageContent;
                  feedbackContainer = botMsg.feedbackContainer;
                  currentMessageElement = messageContent;
                  botMessageCreated = true;
                }
                accumulatedText += data.chunk;
                if (currentMessageElement) {
                  currentMessageElement.html(formatText(accumulatedText));
                  $("#chat-box").scrollTop($("#chat-box")[0].scrollHeight);
                }
              } else if (data.type === "complete") {
                enableUI(); clearTimeout(responseTimeout);
              } else if (data.type === "stopped") {
                if (currentMessageElement) {
                  accumulatedText += "\n\n[Response stopped by user]";
                  currentMessageElement.html(formatText(accumulatedText));
                }
                if (feedbackContainer) {
                  const feedbackButtons = createFeedbackButtons(messageId, userMsg, accumulatedText);
                  feedbackContainer.replaceWith(feedbackButtons);
                }
                enableUI(); clearTimeout(responseTimeout);
              } else if (data.type === "error") {
                if (currentMessageElement) currentMessageElement.html(`<em>Error: ${data.message}</em>`);
                enableUI(); clearTimeout(responseTimeout);
              }
            } catch (e) { console.log("Error parsing JSON:", e); }
          }
        }
      }
    })
    .catch((error) => {
      if (error.name !== "AbortError") {
        if (currentMessageElement) currentMessageElement.html(`<em>Error: ${error.message}</em>`);
        if (feedbackContainer) {
          const feedbackButtons = createFeedbackButtons(messageId, userMsg, accumulatedText);
          feedbackContainer.replaceWith(feedbackButtons);
        }
      }
      enableUI(); clearTimeout(responseTimeout);
    });
  }

  function stopResponse() {
    if (currentController) { currentController.abort(); currentController = null; }
  }

  function createFeedbackButtons(messageId, userMessage, botResponse) {
    const feedbackContainer = $("<div>").addClass("feedback-container");

    const translateBtn = createTranslationButton(messageId, botResponse, feedbackContainer);
    const copyBtn = $("<button>")
      .addClass("feedback-btn copy-btn")
      .attr("title", "Copy response")
      .html(ICONS.copy)
      .click(function () {
  const ICONS = {
    copy: '<svg width="16" height="16" viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><rect x="3" y="3" width="13" height="13" rx="2" fill="none" stroke="currentColor" stroke-width="2"/></svg>',
    thumbUp: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M7 11v9a2 2 0 0 1-2 2H3v-9h2a2 2 0 0 1 2-2z" stroke="currentColor" stroke-width="2"/><path d="M7 11l4.5-7.5A2 2 0 0 1 13.2 3h.8a2 2 0 0 1 2 2v6h3.8a2 2 0 0 1 2 2.2l-1 6A2 2 0 0 1 19 21h-8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    thumbDown: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M7 13V4a2 2 0 0 1 2-2h2v9H9a2 2 0 0 1-2 2z" stroke="currentColor" stroke-width="2"/><path d="M7 13l4.5 7.5A2 2 0 0 0 13.2 21h.8a2 2 0 0 0 2-2v-6h3.8a2 2 0 0 0 2-2.2l-1-6A2 2 0 0 0 19 3h-8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
  };
        const plainText = $("<div>").html(botResponse).text();
        navigator.clipboard.writeText(plainText).then(() => {
          const prev = $(this).html(); $(this).html("✔"); setTimeout(() => $(this).html(prev), 900);
        });
      });

    const thumbsUp = $("<button>").addClass("feedback-btn thumbs-up").attr("data-message-id", messageId).attr("data-feedback", "good").attr("title", "Good response").html(ICONS.thumbUp)
      .click(function(){ submitFeedback(messageId, userMessage, botResponse, "good", $(this)); });
    const thumbsDown = $("<button>").addClass("feedback-btn thumbs-down").attr("data-message-id", messageId).attr("data-feedback", "bad").attr("title", "Bad response").html(ICONS.thumbDown)
      .click(function(){ submitFeedback(messageId, userMessage, botResponse, "bad", $(this)); });

    feedbackContainer.append(translateBtn).append(copyBtn).append(thumbsUp).append(thumbsDown);
    return feedbackContainer;
  }

  function submitFeedback(messageId, userMessage, botResponse, feedback, buttonElement) {
    const container = buttonElement.closest(".feedback-container");
    container.find(".feedback-btn.thumbs-up, .feedback-btn.thumbs-down").prop("disabled", true);
    buttonElement.addClass("selected");

    fetch("/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message_id: messageId, user_message: userMessage, bot_response: botResponse, feedback, session_id: sessionId, timestamp: new Date().toISOString() }),
    })
    .then((r)=>r.json()).then(()=>{
      const thankYou = $("<span>").addClass("thank-you-text").text("Thanks for your feedback!");
      container.append(thankYou); setTimeout(()=> thankYou.fadeOut(), 1600);
    })
    .catch(()=>{
      container.find(".feedback-btn.thumbs-up, .feedback-btn.thumbs-down").prop("disabled", false);
      buttonElement.removeClass("selected");
    });
  }

  function detectLanguage(text) {
    const ru = ["aap","hai","hay","hain","kar","main","yeh","woh","kya","kyun","kab","kahan","kaisa","kitna","mera","tera","hamara","tumhara","unka","iska","uska","nahi","nahin","bahut","shukriya","maaf","ji","han","haan","achha","bura"];
    const lower = (text||"").toLowerCase();
    const words = lower.split(/\s+/); const total = words.length || 1;
    const ruCount = words.filter(w=>ru.includes(w)).length;
    const enWords = (text||"").match(/\b[a-zA-Z]+\b/g) || [];
    const enRatio = enWords.length / total;
    if (total <= 4) { if (ruCount >= 2) return "roman_urdu"; if (enRatio>0.5) return "english"; return "roman_urdu"; }
    if (ruCount >= 2) return "roman_urdu"; if (enRatio>0.35) return "english"; return "english";
  }

  function createTranslationButton(messageId, text, container) {
    const detected = detectLanguage(text);
    const btn = $("<button>").addClass("translate-btn")
      .attr("data-message-id", messageId)
      .attr("data-original-bot-response", text)
      .attr("data-translated-text", "")
      .attr("data-current-lang", detected)
      .attr("title", detected === "english" ? "Translate to Roman Urdu" : "Translate to English")
      .html(detected === "english" ? "Roman Urdu" : "EN")
      .click(function(){ translateMessage($(this)); });
    return btn;
  }

  function translateMessage(buttonElement) {
    const messageId = buttonElement.attr("data-message-id");
    const original = buttonElement.attr("data-original-bot-response");
    const current = buttonElement.attr("data-current-lang");
    const messageContent = buttonElement.closest(".bot-message-wrapper").find(".bot-content-container span");

    buttonElement.html("Translating…").prop("disabled", true);
    const target = current === "english" ? "roman_urdu" : "english";

    fetch("/translate", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: original, target_language: target }),
    })
    .then(r=>r.json()).then(data=>{
      if (data.status === "success") {
        messageContent.html(formatText(data.translated_text));
        if (target === "roman_urdu") buttonElement.html("EN").attr("data-current-lang","roman_urdu").attr("title","Translate to English");
        else buttonElement.html("Roman Urdu").attr("data-current-lang","english").attr("title","Translate to Roman Urdu");
      }
      buttonElement.prop("disabled", false);
    })
    .catch(()=>{ buttonElement.prop("disabled", false).html(target === "roman_urdu" ? "EN" : "Roman Urdu"); });
  }

  function toggleView() {
    const container = document.querySelector(".container");
    const webIcon = document.getElementById("web-icon");
    const mobileIcon = document.getElementById("mobile-icon");
    if (currentView === "web") {
      container.classList.remove("web-view"); container.classList.add("mobile-view");
      webIcon.style.display = "none"; mobileIcon.style.display = "block"; currentView = "mobile";
    } else {
      container.classList.remove("mobile-view"); container.classList.add("web-view");
      webIcon.style.display = "block"; mobileIcon.style.display = "none"; currentView = "web";
    }
  }

  window.sendMessage = sendMessage;
  window.stopResponse = stopResponse;
  window.toggleView = toggleView;

  $(document).ready(function () {
  const ICONS = {
    copy: '<svg width="16" height="16" viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><rect x="3" y="3" width="13" height="13" rx="2" fill="none" stroke="currentColor" stroke-width="2"/></svg>',
    thumbUp: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M7 11v9a2 2 0 0 1-2 2H3v-9h2a2 2 0 0 1 2-2z" stroke="currentColor" stroke-width="2"/><path d="M7 11l4.5-7.5A2 2 0 0 1 13.2 3h.8a2 2 0 0 1 2 2v6h3.8a2 2 0 0 1 2 2.2l-1 6A2 2 0 0 1 19 21h-8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    thumbDown: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M7 13V4a2 2 0 0 1 2-2h2v9H9a2 2 0 0 1-2 2z" stroke="currentColor" stroke-width="2"/><path d="M7 13l4.5 7.5A2 2 0 0 0 13.2 21h.8a2 2 0 0 0 2-2v-6h3.8a2 2 0 0 0 2-2.2l-1-6A2 2 0 0 0 19 3h-8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
  };
    $("#stop-btn").hide();
    $(".container").addClass("web-view"); currentView = "web"; $("#web-icon").show(); $("#mobile-icon").hide();

    setTimeout(() => {
      appendMessage("Hi! I’m the FikrFree Assistant. Ask me about insurance plans, claims, doctor consultations, or e‑pharmacy.", "bot");
    }, 400);

    $("#user-input").on("keypress", function (e) { if (e.key === "Enter" && !$("#user-input").prop("disabled")) sendMessage(); });

    // Speech-to-text support (if available)
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition; let isRecording = false;
    if (SpeechRecognition) {
      recognition = new SpeechRecognition(); recognition.continuous = false; recognition.lang = "en-US";
      $("#mic-btn").on("click", function(){ if (isRecording) recognition.stop(); else recognition.start(); });
      recognition.onstart = function(){ isRecording = true; $("#mic-btn").addClass("recording"); };
      recognition.onend = function(){ isRecording = false; $("#mic-btn").removeClass("recording"); };
      recognition.onresult = function (event) { const transcript = event.results[0][0].transcript; $("#user-input").val(transcript); };
      recognition.onerror = function (event) { isRecording = false; $("#mic-btn").removeClass("recording"); console.warn("Speech recognition error:", event.error); };
    } else { $("#mic-btn").on("click", function(){ alert('Voice input is not supported in this browser. Try Chrome/Edge over HTTPS or localhost.'); }); }
  });
})();
