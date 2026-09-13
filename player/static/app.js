// QuizArena Mobile Player Application Script

let ws = null;
let currentQuizId = null;
let currentParticipantId = null;
let participantName = null;
let sessionToken = null;
let selectedOption = null;
let hasAnswered = false;
let currentMode = "CLASSIC";
let currentLives = 3;
let allowAnswerChange = true;

// DOM Elements
const screens = {
    join: document.getElementById('screen-join'),
    lobby: document.getElementById('screen-lobby'),
    question: document.getElementById('screen-question'),
    buzzer: document.getElementById('screen-buzzer'),
    result: document.getElementById('screen-result'),
    leaderboard: document.getElementById('screen-leaderboard'),
    eliminated: document.getElementById('screen-eliminated'),
    paused: document.getElementById('screen-paused'),
    finished: document.getElementById('screen-finished')
};

// Check for existing session token in localStorage with validation
window.addEventListener('DOMContentLoaded', () => {
    const pathMatch = window.location.pathname.match(/\/join\/([^\/]+)/i);
    const pathCode = pathMatch ? decodeURIComponent(pathMatch[1]).trim().toUpperCase() : "";
    const inputCodeElem = document.getElementById('input-code');
    if (pathCode && inputCodeElem) {
        inputCodeElem.value = pathCode;
        const infoCodeElem = document.getElementById('info-quiz-code');
        if (infoCodeElem) infoCodeElem.innerText = pathCode;
    }
    const urlJoinCode = pathCode || (inputCodeElem ? inputCodeElem.value.trim().toUpperCase() : "");

    const savedToken = localStorage.getItem('qa_session_token');
    const savedCode = localStorage.getItem('qa_join_code');
    const savedId = localStorage.getItem('qa_participant_id');
    const savedName = localStorage.getItem('qa_participant_name');
    const savedQuizId = localStorage.getItem('qa_quiz_id');

    if (urlJoinCode && savedCode && urlJoinCode !== savedCode) {
        console.log("New join code detected from URL. Clearing old session.");
        localStorage.clear();
        showScreen('join');
        return;
    }

    if (savedToken && savedCode && savedId && savedQuizId) {
        fetch(`/api/player/state?quiz_id=${savedQuizId}&participant_id=${savedId}`)
            .then(res => res.json())
            .then(data => {
                if (data && data.status && data.status !== "FINISHED") {
                    currentQuizId = savedQuizId;
                    currentParticipantId = savedId;
                    participantName = savedName;
                    sessionToken = savedToken;
                    initWebSocket();
                } else {
                    localStorage.clear();
                    showScreen('join');
                }
            })
            .catch(err => {
                showScreen('join');
            });
    } else {
        showScreen('join');
    }
});

function showScreen(screenKey) {
    Object.keys(screens).forEach(key => {
        if (screens[key]) {
            screens[key].classList.remove('active');
        }
    });
    if (screens[screenKey]) {
        screens[screenKey].classList.add('active');
    }
}

async function handleJoin(event) {
    event.preventDefault();
    const joinCode = document.getElementById('input-code').value.trim().toUpperCase();
    const name = document.getElementById('input-name').value.trim();
    const teamName = document.getElementById('input-team').value.trim();
    const errorDiv = document.getElementById('join-error');
    const btnJoin = document.getElementById('btn-join');

    errorDiv.classList.add('hidden');
    btnJoin.disabled = true;
    btnJoin.innerText = "Joining...";

    try {
        const response = await fetch('/api/join', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                join_code: joinCode,
                name: name,
                team_name: teamName || null
            })
        });

        const result = await response.json();
        if (!response.ok || !result.success) {
            errorDiv.innerText = result.message || "Failed to join quiz room.";
            errorDiv.classList.remove('hidden');
            btnJoin.disabled = false;
            btnJoin.innerText = "JOIN QUIZ";
            return;
        }

        const data = result.data;
        currentQuizId = data.quiz_id;
        currentParticipantId = data.participant_id;
        sessionToken = data.session_token;
        participantName = data.name;

        localStorage.setItem('qa_session_token', sessionToken);
        localStorage.setItem('qa_join_code', joinCode);
        localStorage.setItem('qa_participant_id', currentParticipantId);
        localStorage.setItem('qa_participant_name', participantName);
        localStorage.setItem('qa_quiz_id', currentQuizId);

        document.getElementById('lobby-quiz-title').innerText = data.quiz_name;
        document.getElementById('btn-leave-room').classList.remove('hidden');
        showScreen('lobby');
        initWebSocket();

    } catch (err) {
        errorDiv.innerText = "Cannot reach server. Please ensure your phone is connected to the same Wi-Fi network as the host computer.";
        errorDiv.classList.remove('hidden');
        btnJoin.disabled = false;
        btnJoin.innerText = "JOIN QUIZ";
    }
}

function leaveRoom() {
    if (confirm("Do you want to leave this quiz room?")) {
        localStorage.clear();
        currentQuizId = null;
        currentParticipantId = null;
        sessionToken = null;
        if (ws) ws.close();
        document.getElementById('btn-leave-room').classList.add('hidden');
        showScreen('join');
    }
}

function initWebSocket() {
    if (!currentQuizId || !currentParticipantId) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/play/${currentQuizId}/${currentParticipantId}`;
    
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log("WebSocket connected to QuizArena server.");
        setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: "PING" }));
            }
        }, 15000);
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleServerEvent(data);
    };

    ws.onclose = () => {
        console.log("WebSocket closed. Attempting reconnect...");
        setTimeout(() => {
            if (sessionToken) initWebSocket();
        }, 3000);
    };
}

function updateLivesDisplay(lives) {
    const livesContainer = document.getElementById('player-lives-container');
    const livesDisplay = document.getElementById('lives-display');
    if (lives !== undefined && lives !== null && currentMode === "SURVIVAL") {
        livesContainer.classList.remove('hidden');
        let hearts = "";
        for (let i = 0; i < lives; i++) hearts += "❤️ ";
        if (lives === 0) hearts = "💀 0 Lives";
        livesDisplay.innerText = hearts.trim();
    } else {
        livesContainer.classList.add('hidden');
    }
}

function togglePlayerSound() {
    if (!window.soundEngine) return;
    const isMuted = window.soundEngine.toggleMute();
    const btn = document.getElementById('btn-sound-toggle');
    if (btn) {
        btn.innerText = isMuted ? '🔇' : '🔊';
        if (isMuted) btn.classList.add('muted');
        else btn.classList.remove('muted');
    }
}

function handleServerEvent(data) {
    const type = data.type;

    if (type === "INIT_STATE") {
        if (data.mode) {
            currentMode = data.mode;
            const modeBadge = document.getElementById('header-mode-badge');
            modeBadge.innerText = data.mode;
            modeBadge.classList.remove('hidden');
        }
        if (data.status === "WAITING" || data.status === "STARTING") {
            showScreen('lobby');
        }
    }
    else if (type === "QUIZ_STARTED") {
        if (data.mode) {
            currentMode = data.mode;
            const modeBadge = document.getElementById('header-mode-badge');
            modeBadge.innerText = data.mode;
            modeBadge.classList.remove('hidden');
        }
        const statusSpan = document.querySelector('#screen-lobby .status-indicator span');
        if (statusSpan) statusSpan.innerText = "🚀 Quiz is starting! Get ready...";
        showScreen('lobby');
    }
    else if (type === "QUESTION_ACTIVE") {
        hasAnswered = false;
        selectedOption = null;
        allowAnswerChange = (data.allow_answer_change !== undefined) ? data.allow_answer_change : true;
        document.getElementById('answer-status-msg').classList.add('hidden');
        document.getElementById('buzz-lock-overlay').classList.add('hidden');
        document.getElementById('second-chance-banner').classList.add('hidden');

        if (data.mode) {
            currentMode = data.mode;
            const modeBadge = document.getElementById('header-mode-badge');
            modeBadge.innerText = data.mode;
            modeBadge.classList.remove('hidden');
        }

        // Start upbeat quiz background music on questions
        if (window.soundEngine) {
            window.soundEngine.startBgMusic();
        }

        if (data.status === "BUZZER_ACTIVE") {
            document.getElementById('buzz-q-text').innerText = data.question.question_text;
            document.getElementById('buzz-timer').innerText = `⏱️ ${data.timer}s`;
            showScreen('buzzer');
        } else {
            renderQuestion(data);
            showScreen('question');
        }
    }
    else if (type === "TIMER_TICK") {
        const timerPills = document.querySelectorAll('.timer-pill');
        timerPills.forEach(pill => pill.innerText = `⏱️ ${data.remaining}s`);

        // Play tick-tock when timer has 5 seconds or less
        if (data.remaining !== undefined && data.remaining <= 5 && data.remaining > 0) {
            if (window.soundEngine) {
                window.soundEngine.playTick(data.remaining % 2 === 0);
            }
        }
    }
    else if (type === "BUZZ_LOCKED") {
        document.getElementById('buzz-winner-name').innerText = data.winner_name;
        document.getElementById('buzz-lock-overlay').classList.remove('hidden');

        const feed = document.getElementById('buzz-feed-list');
        const item = document.createElement('li');
        item.innerText = `⚡ ${data.winner_name} buzzed first!`;
        feed.prepend(item);

        if (data.winner_id === currentParticipantId) {
            setTimeout(() => {
                document.getElementById('buzz-lock-overlay').classList.add('hidden');
                showScreen('question');
            }, 600);
        }
    }
    else if (type === "SECOND_CHANCE") {
        document.getElementById('buzz-winner-name').innerText = data.winner_name;
        const banner = document.getElementById('second-chance-banner');
        banner.innerText = data.message;
        banner.classList.remove('hidden');

        if (data.winner_id === currentParticipantId) {
            setTimeout(() => {
                document.getElementById('buzz-lock-overlay').classList.add('hidden');
                showScreen('question');
            }, 800);
        }
    }
    else if (type === "ANNOUNCEMENT") {
        const banner = document.getElementById('announcement-banner');
        const text = document.getElementById('announcement-text');
        text.innerText = data.message;
        banner.classList.remove('hidden');
        setTimeout(() => {
            banner.classList.add('hidden');
        }, 6000);
    }
    else if (type === "PLAYER_ELIMINATED") {
        if (data.participant_id === currentParticipantId) {
            document.getElementById('eliminated-msg').innerText = data.reason || "You have lost all your lives or were eliminated by the Admin!";
            showScreen('eliminated');
        }
    }
    else if (type === "PLAYER_RESTORED") {
        if (data.participant_id === currentParticipantId) {
            showScreen('lobby');
            pollPlayerState();
        }
    }
    else if (type === "KNOCKOUT_ROUND_END") {
        const elimList = data.eliminated_players || [];
        const isMe = elimList.some(p => p.participant_id === currentParticipantId);
        if (isMe) {
            document.getElementById('eliminated-msg').innerText = `You were eliminated in Round ${data.round}!`;
            showScreen('eliminated');
        }
    }
    else if (type === "QUESTION_RESULT") {
        // Stop background music
        if (window.soundEngine) {
            window.soundEngine.stopBgMusic();
            if (selectedOption) {
                if (selectedOption === data.correct_answer) {
                    window.soundEngine.playCorrect();
                } else {
                    window.soundEngine.playWrong();
                }
            } else {
                window.soundEngine.playWrong();
            }
        }
        renderResult(data);
        showScreen('result');
    }
    else if (type === "LEADERBOARD_UPDATE") {
        if (window.soundEngine) window.soundEngine.stopBgMusic();
        renderLeaderboard(data.leaderboard, data.team_leaderboard);
        showScreen('leaderboard');
    }
    else if (type === "QUIZ_PAUSED") {
        if (window.soundEngine) window.soundEngine.stopBgMusic();
        showScreen('paused');
    }
    else if (type === "QUIZ_RESUMED") {
        if (data.status === "QUESTION_ACTIVE") {
            if (window.soundEngine) window.soundEngine.startBgMusic();
            showScreen('question');
        }
        else if (data.status === "BUZZER_ACTIVE") {
            if (window.soundEngine) window.soundEngine.startBgMusic();
            showScreen('buzzer');
        }
    }
    else if (type === "QUIZ_FINISHED") {
        if (window.soundEngine) {
            window.soundEngine.stopBgMusic();
            window.soundEngine.playFanfare();
        }
        renderFinished(data);
        showScreen('finished');
    }
    else if (type === "MUSIC_TOGGLE") {
        if (window.soundEngine) {
            window.soundEngine.setAdminMute(!data.enabled);
        }
    }
}

function renderQuestion(data) {
    try {
        if (!data || !data.question) return;
        const q = data.question;
        document.getElementById('q-counter').innerText = `Question ${data.current_index || 1} / ${data.total_questions || 1}`;
        document.getElementById('q-timer').innerText = `⏱️ ${data.timer || 30}s`;
        document.getElementById('q-text').innerText = q.question_text || "Question";

        const container = document.getElementById('options-container');
        container.innerHTML = '';

        let opts = q.options || [];
        if (typeof opts === 'string') {
            try { opts = JSON.parse(opts); } catch(e) { opts = []; }
        }

        opts.forEach(optText => {
            const btn = document.createElement('button');
            btn.className = 'option-btn';
            btn.innerText = optText;

            const optLetter = optText.trim()[0];
            btn.onclick = () => selectOption(optLetter, btn);
            container.appendChild(btn);
        });
    } catch(e) {
        console.error("Error rendering question:", e);
    }
}

async function pollPlayerState() {
    if (!currentQuizId || !currentParticipantId) return;
    try {
        const res = await fetch(`/api/player/state?quiz_id=${currentQuizId}&participant_id=${currentParticipantId}`);
        if (res.ok) {
            const data = await res.json();
            handleServerEvent(data);
        }
    } catch(e) {
        console.error("Player state poll error:", e);
    }
}

setInterval(pollPlayerState, 1500);

async function selectOption(letter, btnElement) {
    if (hasAnswered && !allowAnswerChange) return;
    hasAnswered = true;
    selectedOption = letter;

    const buttons = document.querySelectorAll('.option-btn');
    buttons.forEach(b => {
        if (!allowAnswerChange) {
            b.disabled = true;
        }
        b.classList.remove('selected');
    });
    btnElement.classList.add('selected');

    const statusMsg = document.getElementById('answer-status-msg');
    if (statusMsg) {
        statusMsg.innerText = allowAnswerChange 
            ? "✓ Option selected! (You can change it before time runs out)" 
            : "✓ Answer Submitted & Locked In!";
        statusMsg.classList.remove('hidden');
    }

    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: "SUBMIT_ANSWER",
            selected_option: letter
        }));
    } else {
        try {
            await fetch('/api/player/submit_answer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    quiz_id: currentQuizId,
                    participant_id: currentParticipantId,
                    selected_option: letter
                })
            });
        } catch(e) {
            console.error("REST submit error:", e);
        }
    }
}

async function handleBuzz() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: "BUZZ",
            participant_name: participantName
        }));
    } else {
        try {
            await fetch('/api/player/buzz', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    quiz_id: currentQuizId,
                    participant_id: currentParticipantId,
                    participant_name: participantName
                })
            });
        } catch(e) {
            console.error("REST buzz error:", e);
        }
    }
}

function renderResult(data) {
    const stats = data.stats;
    const isUserCorrect = (data.correct_answer === selectedOption);

    const iconWrapper = document.getElementById('result-icon-wrapper');
    const icon = document.getElementById('result-icon');
    const title = document.getElementById('result-title');
    const userAns = document.getElementById('result-user-ans');

    if (selectedOption) {
        if (isUserCorrect) {
            iconWrapper.className = 'icon-circle correct';
            icon.innerText = '✓';
            title.innerText = 'Correct!';
            userAns.innerText = `Your answer: ${selectedOption}`;
        } else {
            iconWrapper.className = 'icon-circle wrong';
            icon.innerText = '✗';
            title.innerText = 'Incorrect';
            userAns.innerText = `Your answer: ${selectedOption} (Correct: ${data.correct_answer})`;
        }
    } else {
        iconWrapper.className = 'icon-circle wrong';
        icon.innerText = '⏱️';
        title.innerText = 'Time Up!';
        userAns.innerText = `Correct Answer: ${data.correct_answer}`;
    }

    document.getElementById('stat-correct').innerText = stats.correct;
    document.getElementById('stat-wrong').innerText = stats.wrong;
    document.getElementById('stat-noans').innerText = stats.no_answer;

    if (stats.fastest && stats.fastest !== "None") {
        document.getElementById('fastest-name').innerText = stats.fastest;
        document.getElementById('fastest-callout').classList.remove('hidden');
    }

    if (data.explanation) {
        document.getElementById('explanation-text').innerText = data.explanation;
        document.getElementById('explanation-box').classList.remove('hidden');
    }
}

function renderLeaderboard(leaderboard, teamLeaderboard) {
    const list = document.getElementById('leaderboard-list');
    list.innerHTML = '';

    const teamContainer = document.getElementById('team-lb-container');
    const teamList = document.getElementById('team-leaderboard-list');

    if (teamLeaderboard && teamLeaderboard.length > 0) {
        teamContainer.classList.remove('hidden');
        teamList.innerHTML = '';
        teamLeaderboard.forEach(t => {
            const li = document.createElement('li');
            li.className = 'lb-item';
            li.innerHTML = `
                <span class="lb-rank">#${t.rank}</span>
                <span class="lb-name">👥 ${t.name}</span>
                <span class="lb-score">${t.score} pts</span>
            `;
            teamList.appendChild(li);
        });
    } else {
        teamContainer.classList.add('hidden');
    }

    leaderboard.forEach(item => {
        const li = document.createElement('li');
        li.className = 'lb-item';
        
        let medal = `#${item.rank}`;
        if (item.rank === 1) medal = '🥇';
        if (item.rank === 2) medal = '🥈';
        if (item.rank === 3) medal = '🥉';

        let livesStr = (item.lives !== undefined && currentMode === "SURVIVAL") ? ` (${item.lives} ❤️)` : '';

        li.innerHTML = `
            <span class="lb-rank">${medal}</span>
            <span class="lb-name">${item.name}${livesStr}</span>
            <span class="lb-score">${item.score} pts</span>
        `;
        list.appendChild(li);
    });
}

function renderFinished(data) {
    if (data.winner) {
        document.getElementById('winner-name').innerText = data.winner.name;
    }
    if (data.leaderboard) {
        const list = document.getElementById('final-leaderboard-list');
        list.innerHTML = '';
        data.leaderboard.slice(0, 10).forEach(item => {
            const li = document.createElement('li');
            li.className = 'lb-item';
            li.innerHTML = `
                <span class="lb-rank">#${item.rank}</span>
                <span class="lb-name">${item.name}</span>
                <span class="lb-score">${item.score} pts</span>
            `;
            list.appendChild(li);
        });
    }

    // 🎈 Launch balloon celebration!
    launchBalloons();
}

/* =========================================================
   BALLOON CELEBRATION ENGINE
   ========================================================= */

const BALLOON_COLORS = [
    '#FF4B4B', // red
    '#FF8C42', // orange
    '#FFD700', // gold
    '#4ADE80', // green
    '#60A5FA', // blue
    '#A78BFA', // purple
    '#F472B6', // pink
    '#34D399', // teal
    '#FCA5A5', // light red
    '#93C5FD', // light blue
];

let balloonInterval = null;
let balloonCount = 0;
const TOTAL_BALLOONS = 30; // Total balloons to launch in the celebration

function launchBalloons() {
    const container = document.getElementById('balloon-container');
    if (!container) return;

    container.innerHTML = '';
    container.style.pointerEvents = 'auto';
    balloonCount = 0;

    // Enable balloon container for pointer interaction
    clearInterval(balloonInterval);

    // Spawn balloons in staggered waves
    balloonInterval = setInterval(() => {
        if (balloonCount >= TOTAL_BALLOONS) {
            clearInterval(balloonInterval);
            return;
        }
        spawnBalloon(container);
        balloonCount++;
    }, 280);
}

function spawnBalloon(container) {
    const balloon = document.createElement('div');
    balloon.className = 'balloon';

    // Random horizontal position
    const leftPct = 4 + Math.random() * 88;  // 4% - 92%
    balloon.style.left = `${leftPct}%`;

    // Random color
    const color = BALLOON_COLORS[Math.floor(Math.random() * BALLOON_COLORS.length)];
    balloon.style.background = `radial-gradient(circle at 35% 35%, ${lightenColor(color, 40)}, ${color} 70%)`;

    // Random size variance (+/- 12px)
    const sizeVariance = Math.floor(Math.random() * 12);
    balloon.style.width = `${52 + sizeVariance}px`;
    balloon.style.height = `${68 + Math.floor(sizeVariance * 1.3)}px`;

    // Random float duration: 6 – 11 seconds
    const duration = 6 + Math.random() * 5;
    balloon.style.animationDuration = `${duration}s`;

    // Random slight rotation offset
    const rotOffset = (Math.random() - 0.5) * 20;
    balloon.style.setProperty('--rot', `${rotOffset}deg`);

    // Gloss highlight
    const shine = document.createElement('div');
    shine.className = 'balloon-shine';
    balloon.appendChild(shine);

    // Knot
    const knot = document.createElement('div');
    knot.className = 'balloon-knot';
    knot.style.background = color;
    balloon.appendChild(knot);

    // String
    const string = document.createElement('div');
    string.className = 'balloon-string';
    balloon.appendChild(string);

    // Pop on click / tap
    balloon.addEventListener('click', (e) => popBalloon(balloon, e, color));
    balloon.addEventListener('touchstart', (e) => {
        e.preventDefault();
        popBalloon(balloon, e.touches[0], color);
    }, { passive: false });

    container.appendChild(balloon);

    // Auto-remove after animation ends
    balloon.addEventListener('animationend', () => {
        if (balloon.parentNode) balloon.parentNode.removeChild(balloon);
    });
}

function popBalloon(balloon, event, color) {
    if (balloon.classList.contains('popping')) return;
    balloon.classList.add('popping');

    // Confetti burst
    const rect = balloon.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    spawnConfetti(cx, cy, color);

    setTimeout(() => {
        if (balloon.parentNode) balloon.parentNode.removeChild(balloon);
    }, 230);
}

function spawnConfetti(cx, cy, baseColor) {
    const container = document.getElementById('balloon-container');
    if (!container) return;

    const colors = [baseColor, '#FFD700', '#FFFFFF', lightenColor(baseColor, 60)];
    const NUM_PIECES = 10;

    for (let i = 0; i < NUM_PIECES; i++) {
        const piece = document.createElement('div');
        piece.className = 'balloon-confetti';

        // Position relative to viewport
        piece.style.position = 'fixed';
        piece.style.left = `${cx}px`;
        piece.style.top = `${cy}px`;
        piece.style.background = colors[Math.floor(Math.random() * colors.length)];

        const angle = (i / NUM_PIECES) * 360 + Math.random() * 30;
        const dist = 40 + Math.random() * 50;
        const rad = (angle * Math.PI) / 180;
        const tx = Math.cos(rad) * dist;
        const ty = Math.sin(rad) * dist;

        piece.style.setProperty('--tx', `${tx}px`);
        piece.style.setProperty('--ty', `${ty}px`);

        document.body.appendChild(piece);
        piece.addEventListener('animationend', () => {
            if (piece.parentNode) piece.parentNode.removeChild(piece);
        });
    }
}

function lightenColor(hex, amount) {
    // Lighten a hex color by mixing with white
    hex = hex.replace('#', '');
    const r = Math.min(255, parseInt(hex.substring(0, 2), 16) + amount);
    const g = Math.min(255, parseInt(hex.substring(2, 4), 16) + amount);
    const b = Math.min(255, parseInt(hex.substring(4, 6), 16) + amount);
    return `rgb(${r}, ${g}, ${b})`;
}

function stopBalloons() {
    clearInterval(balloonInterval);
    const container = document.getElementById('balloon-container');
    if (container) {
        container.innerHTML = '';
        container.style.pointerEvents = 'none';
    }
}
