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
  let autoMode = true; // auto-resize driven view until user toggles manually
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

    // Convert Markdown tables first: contiguous blocks starting with '|' rows
    const rawLines = t.split(/\n/);
    let i = 0; let tableConverted = [];
    while (i < rawLines.length) {
      if (/^\s*\|.*\|\s*$/.test(rawLines[i])) {
        const block = [];
        while (i < rawLines.length && /^\s*\|.*\|\s*$/.test(rawLines[i])) {
          block.push(rawLines[i]); i++;
        }
        // Expect at least header + separator
        if (block.length >= 2) {
          const rows = block.map(l => l.trim().slice(1, -1).split('|').map(c => c.trim()));
          const header = rows[0];
          const body = rows.slice(2); // skip separator row
          let tableHTML = "<table class='md-table' style='border-collapse:collapse;margin:6px 0;width:100%'>";
          tableHTML += "<thead><tr>" + header.map(h => `<th style='border-bottom:1px solid #ddd;text-align:left;padding:4px 6px;'>${h}</th>`).join("") + "</tr></thead>";
          tableHTML += "<tbody>" + body.map(r => "<tr>" + r.map(c => `<td style='border-bottom:1px solid #eee;padding:4px 6px;'>${c}</td>`).join("") + "</tr>").join("") + "</tbody>";
          tableHTML += "</table>";
          tableConverted.push(tableHTML);
          continue;
        }
      }
      tableConverted.push(rawLines[i]); i++;
    }

    // Convert consecutive lines starting with "- " into an unordered list
    const lines = tableConverted.flatMap(l => typeof l === 'string' ? l.split(/\n/) : [l]);
    let html = "";
    let inList = false;
    for (const line of lines) {
      if (line.startsWith('<table')) { if (inList) { html += "</ul>"; inList = false; } html += line; continue; }
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
    // Log send click and start timer
    let responseTimeout = setTimeout(() => {
      if ($("#send-btn").prop("disabled")) {
        if (currentMessageElement) currentMessageElement.html("<em>Error: Response timed out. Please try again.</em>");
        enableUI();
      }
    }, 60000);

    const input = $("#user-input");
    const userMsg = input.val().trim();
    if (!userMsg) return;

    try { logEvent('send_clicked', { prompt_len: userMsg.length }); } catch(_) {}
    const t0 = (typeof performance !== 'undefined' ? performance.now() : Date.now());
    let firstTokenLogged = false;
    let shortlistLogged = false;

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
                if (!firstTokenLogged) {
                  const t1 = (typeof performance !== 'undefined' ? performance.now() : Date.now());
                  try { logEvent('first_token', { duration_ms: Math.round(t1 - t0) }); } catch(_) {}
                  firstTokenLogged = true;
                }
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
                // Detect shortlist table/header once per message
                if (!shortlistLogged && (/\|\s*Plan\s*\|\s*Variant\s*\|/.test(accumulatedText) || /###\s*Recommended Plans/.test(accumulatedText))) {
                  try { logEvent('shortlist_shown', { length_chars: accumulatedText.length }); } catch(_) {}
                  shortlistLogged = true;
                }
              } else if (data.type === "complete") {
                const t2 = (typeof performance !== 'undefined' ? performance.now() : Date.now());
                try { logEvent('response_complete', { duration_ms: Math.round(t2 - t0), chars: accumulatedText.length }); } catch(_) {}
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
                try { logEvent('error', { scope: 'chat_stream', message: data.message }); } catch(_) {}
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
        try { logEvent('error', { scope: 'chat_fetch', message: error.message }); } catch(_) {}
      }
      enableUI(); clearTimeout(responseTimeout);
    });
  }

  function stopResponse() {
    if (currentController) { currentController.abort(); currentController = null; }
    try { logEvent('stop_clicked', {}); } catch(_) {}
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

    // Quick actions: Compare / Start quote
    // Extract the first plan from this bot message (Plan — Variant)
    function extractFirstPlan(text){
      const lines = (text||"").split(/\n/);
      // 1) Table row after header
      let inTable = false, headers = [];
      for (let i=0;i<lines.length;i++){
        const l = lines[i].trim();
        if (/^\|.*\|$/.test(l)){
          const cells = l.slice(1,-1).split('|').map(s=>s.trim());
          if (!inTable){ inTable = true; headers = cells; continue; }
          if (cells.length === headers.length){
            const planIdx = headers.findIndex(h=>/plan/i.test(h));
            const varIdx = headers.findIndex(h=>/variant/i.test(h));
            if (planIdx>=0 && varIdx>=0){
              return { plan: cells[planIdx], variant: cells[varIdx] };
            }
          }
          continue;
        } else { inTable = false; }
        // 2) Headings/Bullets/Numbered with known variant list
        const m = l.match(/^\s*(?:#{1,6}\s*)?(?:\d+[\).\-]\s*)?(?:\*\*)?\s*(.+?)\s*(?:\*\*)?\s*[—-]\s*(?:\*\*)?\s*(Bronze|Silver|Gold|Platinum|Diamond|Ace|Crown|Default)\b/i);
        if (m) return { plan: m[1].trim(), variant: m[2].trim() };
      }
      return null;
    }

    const firstPlan = extractFirstPlan(botResponse);

    const suggestBtn = $("<button>")
      .addClass("action-chip")
      .attr("title", "Suggest a similar plan")
      .html('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3v3M5.2 7.2l2.1 2.1M3 12h3m9-6l2.1 2.1M18 12h3M8 17l-1 4 4-1 5-5a4 4 0 1 0-8 0Z"/></svg><span>Suggest</span>')
      .click(function(){
        if (firstPlan){
          const msg = `SUGGEST_ALTERNATIVE: ${firstPlan.plan} — ${firstPlan.variant}`;
          sendMessageByText(msg);
        } else {
          sendMessageByText('Suggest a similar plan for my needs');
        }
      });
    const quoteBtn = $("<button>")
      .addClass("action-chip primary")
      .attr("title", "Start quote")
      .html('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14"/><path d="M12 5l7 7-7 7"/></svg><span>Start quote</span>')
      .click(function(){ openLeadForm(); });

    feedbackContainer.append(translateBtn).append(suggestBtn).append(quoteBtn).append(copyBtn).append(thumbsUp).append(thumbsDown);
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
    const globe = '<svg aria-hidden="true" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"/></svg>';
    const label = detected === "english" ? "Roman Urdu" : "EN";
    const btn = $("<button>").addClass("translate-btn")
      .attr("data-message-id", messageId)
      .attr("data-original-bot-response", text)
      .attr("data-translated-text", "")
      .attr("data-current-lang", detected)
      .attr("title", detected === "english" ? "Translate to Roman Urdu" : "Translate to English")
      .html(globe + '<span class="btn-label">' + label + '</span>')
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
    try { logEvent('translate_clicked', { target }); } catch(_) {}

    fetch("/translate", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: original, target_language: target }),
    })
    .then(r=>r.json()).then(data=>{
      if (data.status === "success") {
        messageContent.html(formatText(data.translated_text));
        const globe = '<svg aria-hidden="true" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"/></svg>';
        if (target === "roman_urdu") buttonElement.html('EN').attr("data-current-lang","roman_urdu").attr("title","Translate to English");
        else buttonElement.html(globe + '<span class="btn-label">Roman Urdu</span>').attr("data-current-lang","english").attr("title","Translate to Roman Urdu");
        try { logEvent('translate_complete', { target }); } catch(_) {}
      }
      buttonElement.prop("disabled", false);
    })
    .catch((err)=>{ 
      const globe = '<svg aria-hidden="true" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"/></svg>';
      buttonElement.prop("disabled", false).html(target === "roman_urdu" ? "EN" : globe + '<span class="btn-label">Roman Urdu</span>'); 
      try { logEvent('error', { scope: 'translate', message: err?.message || 'translate_failed' }); } catch(_) {}
    });
  }

  function setViewState(view) {
    const container = document.querySelector(".container");
    const webIcon = document.getElementById("web-icon");
    const mobileIcon = document.getElementById("mobile-icon");
    if (!container || !webIcon || !mobileIcon) return;
    if (view === "mobile") {
      container.classList.remove("web-view");
      container.classList.add("mobile-view");
      webIcon.style.display = "none";
      mobileIcon.style.display = "block";
      currentView = "mobile";
    } else {
      container.classList.remove("mobile-view");
      container.classList.add("web-view");
      webIcon.style.display = "block";
      mobileIcon.style.display = "none";
      currentView = "web";
    }
  }

  function setViewByWidth() {
    const w = window.innerWidth || document.documentElement.clientWidth;
    const target = w <= 480 ? "mobile" : "web";
    if (target !== currentView) setViewState(target);
  }

  function toggleView() {
    autoMode = false; // user takes control
    setViewState(currentView === "web" ? "mobile" : "web");
  }

  // --- Lead capture ---
  function openLeadForm() { document.getElementById('lead-modal').style.display = 'block'; }
  function closeLeadForm() { document.getElementById('lead-modal').style.display = 'none'; }
  function submitLeadForm(e) {
    e.preventDefault();
    const status = document.getElementById('lead-status');
    status.textContent = 'Submitting…';
    const payload = {
      consent: document.getElementById('lead-consent').checked,
      name: document.getElementById('lead-name').value.trim() || null,
      age: parseInt(document.getElementById('lead-age').value || '0', 10) || null,
      city: document.getElementById('lead-city').value.trim() || null,
      dependents: parseInt(document.getElementById('lead-dependents').value || '0', 10) || null,
      budget_pkr: parseFloat(document.getElementById('lead-budget').value || '0') || null,
      intent: document.getElementById('lead-intent').value,
      product_interest: document.getElementById('lead-product').value.trim() || null,
      session_id: sessionId,
    };
    fetch('/api/v1/leads', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(data => {
      if (data.status === 'success') {
        status.style.color = '#0a7d2a';
        status.textContent = 'Thanks! A specialist will reach out.';
        // Log a minimal lead_submitted event without PII
        const meta = { 
          city: payload.city || undefined,
          age_band: payload.age ? (payload.age < 25 ? '<25' : payload.age < 40 ? '25-39' : payload.age < 60 ? '40-59' : '60+') : undefined,
          dependents: payload.dependents || 0,
          budget_pkr: payload.budget_pkr || undefined,
          intent: payload.intent,
          product_interest: payload.product_interest || undefined
        };
        try { logEvent('lead_submitted', meta); } catch(_) {}
        setTimeout(() => { closeLeadForm(); status.textContent=''; }, 1200);
      } else {
        status.style.color = '#b00020';
        status.textContent = data.message || 'Could not submit lead.';
      }
    })
    .catch(err => { status.style.color = '#b00020'; status.textContent = err.message || 'Network error'; });
  }

  window.sendMessage = sendMessage;
  window.stopResponse = stopResponse;
  window.toggleView = toggleView;
  window.openLeadForm = openLeadForm;
  window.closeLeadForm = closeLeadForm;
  window.submitLeadForm = submitLeadForm;
  window.sendMessageByText = function(text){ const input = $("#user-input"); input.val(text); sendMessage(); }

  // --- Events logging ---
  function logEvent(event, metadata = {}) {
    try {
      fetch('/api/v1/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event, session_id: sessionId, metadata })
      }).catch(() => {});
    } catch (_) { /* ignore */ }
  }

  function showToast(message, ok = true) {
    const el = document.createElement('div');
    el.textContent = message;
    el.setAttribute('role', 'status');
    el.style.position = 'fixed';
    el.style.bottom = '18px';
    el.style.right = '18px';
    el.style.padding = '10px 12px';
    el.style.borderRadius = '8px';
    el.style.background = ok ? '#0a7d2a' : '#b00020';
    el.style.color = '#fff';
    el.style.boxShadow = '0 4px 16px rgba(0,0,0,0.2)';
    el.style.zIndex = '2000';
    document.body.appendChild(el);
    setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity .3s'; }, 1100);
    setTimeout(() => { el.remove(); }, 1500);
  }

  window.logEvent = logEvent;
  window.showToast = showToast;

  $(document).ready(function () {
  const ICONS = {
    copy: '<svg width="16" height="16" viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><rect x="3" y="3" width="13" height="13" rx="2" fill="none" stroke="currentColor" stroke-width="2"/></svg>',
    thumbUp: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M7 11v9a2 2 0 0 1-2 2H3v-9h2a2 2 0 0 1 2-2z" stroke="currentColor" stroke-width="2"/><path d="M7 11l4.5-7.5A2 2 0 0 1 13.2 3h.8a2 2 0 0 1 2 2v6h3.8a2 2 0 0 1 2 2.2l-1 6A2 2 0 0 1 19 21h-8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    thumbDown: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M7 13V4a2 2 0 0 1 2-2h2v9H9a2 2 0 0 1-2 2z" stroke="currentColor" stroke-width="2"/><path d="M7 13l4.5 7.5A2 2 0 0 0 13.2 21h.8a2 2 0 0 0 2-2v-6h3.8a2 2 0 0 0 2-2.2l-1-6A2 2 0 0 0 19 3h-8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
  };
    $("#stop-btn").hide();

    // Enhance footer buttons with icons + labels (labels hidden on mobile via CSS)
    const sendBtn = $("#send-btn");
    if (sendBtn.length && !sendBtn.data('iconified')) {
      sendBtn
        .addClass('icon-label-btn')
        .html('<svg aria-hidden="true" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14"/><path d="M12 5l7 7-7 7"/></svg><span class="btn-label">Send</span>')
        .attr('aria-label','Send')
        .attr('title','Send')
        .data('iconified', true);
    }
    const leadBtn = $("#lead-btn");
    if (leadBtn.length && !leadBtn.data('iconified')) {
      // Simple document/quote icon
      leadBtn
        .addClass('icon-label-btn')
        .html('<svg aria-hidden="true" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 7h8M8 11h8M8 15h5"/></svg><span class="btn-label">Get Quote</span>')
        .attr('aria-label','Get quote')
        .attr('title','Get quote')
        .data('iconified', true);
    }
    const stopBtn = $("#stop-btn");
    if (stopBtn.length && !stopBtn.data('iconified')) {
      // Stop square icon
      stopBtn
        .addClass('icon-label-btn')
        .html('<svg aria-hidden="true" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><rect x="7" y="7" width="10" height="10" rx="2"/></svg><span class="btn-label">Stop</span>')
        .attr('aria-label','Stop response')
        .attr('title','Stop response')
        .data('iconified', true);
    }
    // Initialize view responsively
    setViewByWidth();
    if (!document.querySelector('.container').classList.contains('web-view') &&
        !document.querySelector('.container').classList.contains('mobile-view')) {
      // Fallback if setViewByWidth did not execute
      setViewState("web");
    }

    // Adjust view on resize unless user manually toggled
    let resizeTimer = null;
    window.addEventListener('resize', function(){
      if (!autoMode) return;
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(setViewByWidth, 120);
    });

    setTimeout(() => {
      appendMessage("Hi! I’m the FikrFree Assistant. Ask me about insurance plans, claims, doctor consultations, or e‑pharmacy.", "bot");
    }, 400);

    $("#user-input").on("keypress", function (e) { if (e.key === "Enter" && !$("#user-input").prop("disabled")) sendMessage(); });

    // Wire optional Event button if present
    const eventBtn = document.getElementById('event-btn');
    if (eventBtn) {
      eventBtn.addEventListener('click', function(){
        logEvent('event_button_clicked', { location: 'ui', ts: Date.now() });
        showToast('Event logged');
      });
    }

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
