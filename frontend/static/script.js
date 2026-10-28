// ==================== GET ELEMENTS ====================
const chatIcon = document.getElementById('chatIcon');
const chatPopup = document.getElementById('chatPopup');
const closeChat = document.getElementById('closeChat');
const clearChat = document.getElementById('clearChat');
const sendBtn = document.getElementById('sendBtn');
const userInput = document.getElementById('userInput');
const chatBody = document.getElementById('chatBody');

// ==================== SESSION ID ====================
let sessionId = localStorage.getItem('chatSessionId');
if (!sessionId) {
    sessionId = 'session_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('chatSessionId', sessionId);
}

// ==================== MESSAGE STORAGE ====================
let messages = [];

function loadMessages() {
    const saved = localStorage.getItem('chatMessages');
    if (saved) {
        messages = JSON.parse(saved);
        renderMessages();
    } else {
        addMessage("Hello! How can I help you today?", 'bot');
    }
}

function saveMessages() {
    localStorage.setItem('chatMessages', JSON.stringify(messages));
}

function renderMessages() {
    chatBody.innerHTML = '';
    messages.forEach(msg => {
        appendMessageToDOM(msg.text, msg.sender, msg.timestamp, msg.originalQuestion, msg.sources, msg.isSubstantive);
    });
    chatBody.scrollTop = chatBody.scrollHeight;
}

// ==================== FORMAT MESSAGE TEXT ====================
function formatMessageText(text) {
    const lines = text.split('\n');
    let inList = false;
    let listType = null;
    let formatted = '';

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const bulletMatch = line.match(/^[-*]\s+(.*)/);
        const numberMatch = line.match(/^(\d+)\.\s+(.*)/);

        if (bulletMatch) {
            if (!inList || listType !== 'ul') {
                if (inList) formatted += `</${listType}>`;
                formatted += '<ul>';
                inList = true;
                listType = 'ul';
            }
            formatted += `<li>${bulletMatch[1]}</li>`;
        } else if (numberMatch) {
            if (!inList || listType !== 'ol') {
                if (inList) formatted += `</${listType}>`;
                formatted += '<ol>';
                inList = true;
                listType = 'ol';
            }
            formatted += `<li>${numberMatch[2]}</li>`;
        } else {
            if (inList) {
                formatted += `</${listType}>`;
                inList = false;
                listType = null;
            }
            const escaped = line.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            formatted += (escaped ? escaped + '<br>' : '');
        }
    }
    if (inList) {
        formatted += `</${listType}>`;
    }
    return formatted;
}

// ==================== CREATE MESSAGE ELEMENT ====================
function appendMessageToDOM(text, sender, timestamp, originalQuestion = null, sources = [], isSubstantive = false) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', sender === 'user' ? 'user-message' : 'bot-message');

    // Avatar
    const avatar = document.createElement('div');
    avatar.classList.add('avatar');
    avatar.innerHTML = sender === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';
    msgDiv.appendChild(avatar);

    // Content wrapper
    const contentDiv = document.createElement('div');
    contentDiv.classList.add('message-content');

    // Message text (formatted)
    const textDiv = document.createElement('div');
    textDiv.classList.add('message-text');
    textDiv.innerHTML = formatMessageText(text);
    contentDiv.appendChild(textDiv);

    // Timestamp
    const timeDiv = document.createElement('div');
    timeDiv.classList.add('timestamp');
    const date = new Date(timestamp);
    timeDiv.textContent = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    contentDiv.appendChild(timeDiv);

    // Action buttons (only for bot messages that are substantive)
    if (sender === 'bot' && isSubstantive) {
        const buttonContainer = document.createElement('div');
        buttonContainer.classList.add('action-buttons');

        // Deep Explanation (if originalQuestion exists)
        if (originalQuestion) {
            const deepBtn = document.createElement('button');
            deepBtn.classList.add('action-btn');
            deepBtn.innerHTML = '<i class="fas fa-chevron-circle-down"></i> Deep';
            deepBtn.addEventListener('click', () => askDeeper(originalQuestion));
            buttonContainer.appendChild(deepBtn);
        }

        // Show Source
        if (sources && sources.length > 0) {
            const sourceBtn = document.createElement('button');
            sourceBtn.classList.add('action-btn');
            sourceBtn.innerHTML = '<i class="fas fa-file-pdf"></i> Source';
            sourceBtn.addEventListener('click', () => showSource());
            buttonContainer.appendChild(sourceBtn);
        }

        // Tell Me More
        const tellMoreBtn = document.createElement('button');
        tellMoreBtn.classList.add('action-btn');
        tellMoreBtn.innerHTML = '<i class="fas fa-question-circle"></i> Tell More';
        tellMoreBtn.addEventListener('click', () => tellMore());
        buttonContainer.appendChild(tellMoreBtn);

        // Summarize
        const summarizeBtn = document.createElement('button');
        summarizeBtn.classList.add('action-btn');
        summarizeBtn.innerHTML = '<i class="fas fa-compress-alt"></i> Summarize';
        summarizeBtn.addEventListener('click', () => summarize());
        buttonContainer.appendChild(summarizeBtn);

        // Simplify (Explain Like I'm 5)
        const simplifyBtn = document.createElement('button');
        simplifyBtn.classList.add('action-btn');
        simplifyBtn.innerHTML = '<i class="fas fa-child"></i> Simplify';
        simplifyBtn.addEventListener('click', () => simplify());
        buttonContainer.appendChild(simplifyBtn);

        contentDiv.appendChild(buttonContainer);
    }

    msgDiv.appendChild(contentDiv);
    chatBody.appendChild(msgDiv);
}

// Add a message to history and DOM
function addMessage(text, sender, originalQuestion = null, sources = [], isSubstantive = false) {
    const timestamp = Date.now();
    messages.push({ text, sender, timestamp, originalQuestion, sources, isSubstantive });
    appendMessageToDOM(text, sender, timestamp, originalQuestion, sources, isSubstantive);
    saveMessages();
    chatBody.scrollTop = chatBody.scrollHeight;
}

// ==================== TYPING INDICATOR ====================
function appendTypingIndicator() {
    const indicator = document.createElement('div');
    indicator.classList.add('typing-indicator');
    indicator.innerHTML = '<span></span><span></span><span></span>';
    chatBody.appendChild(indicator);
    chatBody.scrollTop = chatBody.scrollHeight;
    return indicator;
}

// ==================== FOLLOW-UP ACTIONS ====================
async function askDeeper(question) {
    const systemMsgDiv = document.createElement('div');
    systemMsgDiv.classList.add('system-message');
    systemMsgDiv.innerHTML = `<i class="fas fa-robot"></i> Requesting deeper explanation...`;
    chatBody.appendChild(systemMsgDiv);
    chatBody.scrollTop = chatBody.scrollHeight;

    const typingIndicator = appendTypingIndicator();

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                question: question, 
                deeper: true,
                sessionId: sessionId 
            })
        });
        const data = await response.json();
        typingIndicator.remove();
        systemMsgDiv.remove();
        addMessage(data.answer, 'bot', question, data.sources || [], data.is_substantive);
    } catch (error) {
        typingIndicator.remove();
        systemMsgDiv.remove();
        addMessage('Error connecting to server.', 'bot');
        console.error(error);
    }
}

async function showSource() {
    const typingIndicator = appendTypingIndicator();
    try {
        const response = await fetch('/source', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sessionId })
        });
        const data = await response.json();
        typingIndicator.remove();
        // Show source as a system message, not a full bot message
        const sourceDiv = document.createElement('div');
        sourceDiv.classList.add('system-message');
        sourceDiv.innerHTML = `<i class="fas fa-info-circle"></i> ${data.answer.replace(/\n/g, '<br>')}`;
        chatBody.appendChild(sourceDiv);
        chatBody.scrollTop = chatBody.scrollHeight;
    } catch (error) {
        typingIndicator.remove();
        console.error(error);
    }
}

async function tellMore() {
    const typingIndicator = appendTypingIndicator();
    try {
        const response = await fetch('/tellmore', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sessionId })
        });
        const data = await response.json();
        typingIndicator.remove();
        addMessage(data.answer, 'bot', null, [], true);
    } catch (error) {
        typingIndicator.remove();
        console.error(error);
    }
}

async function summarize() {
    const typingIndicator = appendTypingIndicator();
    try {
        const response = await fetch('/summarize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sessionId })
        });
        const data = await response.json();
        typingIndicator.remove();
        addMessage(data.answer, 'bot', null, [], true);
    } catch (error) {
        typingIndicator.remove();
        console.error(error);
    }
}

async function simplify() {
    const typingIndicator = appendTypingIndicator();
    try {
        const response = await fetch('/simplify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sessionId, question: "Explain this simply" })
        });
        const data = await response.json();
        typingIndicator.remove();
        addMessage(data.answer, 'bot', null, [], true);
    } catch (error) {
        typingIndicator.remove();
        console.error(error);
    }
}

// ==================== SEND MESSAGE ====================
sendBtn.addEventListener('click', async () => {
    const message = userInput.value.trim();
    if (!message) return;

    addMessage(message, 'user');
    userInput.value = '';

    const typingIndicator = appendTypingIndicator();

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                question: message, 
                deeper: false,
                sessionId: sessionId 
            })
        });
        const data = await response.json();
        typingIndicator.remove();
        addMessage(data.answer, 'bot', message, data.sources || [], data.is_substantive);
    } catch (error) {
        typingIndicator.remove();
        addMessage('Error connecting to server. Make sure the backend is running.', 'bot');
        console.error(error);
    }
});

// ==================== ENTER KEY ====================
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendBtn.click();
    }
});

// ==================== CLEAR CHAT ====================
clearChat.addEventListener('click', () => {
    messages = [];
    localStorage.removeItem('chatMessages');
    chatBody.innerHTML = '';
    addMessage("Hello! How can I help you today?", 'bot');
});

// ==================== TOGGLE POPUP ====================
chatIcon.addEventListener('click', () => {
    chatPopup.style.display = 'flex';
    loadMessages();
});

closeChat.addEventListener('click', () => {
    chatPopup.style.display = 'none';
});