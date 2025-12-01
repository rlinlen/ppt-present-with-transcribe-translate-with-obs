let ws = null;
let reconnectInterval = null;
const subtitleOriginal = document.getElementById('subtitle-original');
const subtitleTranslation = document.getElementById('subtitle-translation');
const subtitleContainer = document.getElementById('subtitle-container');

// Load config and apply fullscreen mode if enabled
fetch('/config')
    .then(res => res.json())
    .then(config => {
        if (config.fullscreen_mode) {
            document.body.classList.add('fullscreen-mode');
        }
    })
    .catch(err => console.error('Failed to load config:', err));

function connect() {
    ws = new WebSocket('ws://localhost:8000/ws');
    
    ws.onopen = () => {
        console.log('Connected to transcription server');
        if (reconnectInterval) {
            clearInterval(reconnectInterval);
            reconnectInterval = null;
        }
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateSubtitle(data);
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
    
    ws.onclose = () => {
        console.log('Disconnected from server. Reconnecting...');
        if (!reconnectInterval) {
            reconnectInterval = setInterval(() => {
                connect();
            }, 3000);
        }
    };
}

function updateSubtitle(data) {
    if (data.transcript && data.transcript.trim()) {
        subtitleOriginal.textContent = data.transcript;
        subtitleOriginal.style.opacity = '1';
        setTimeout(() => {
            subtitleOriginal.scrollTop = subtitleOriginal.scrollHeight;
        }, 0);
    } else if (!data.is_partial) {
        subtitleOriginal.style.opacity = '0';
    }
    
    if (data.translation && data.translation.trim()) {
        subtitleTranslation.textContent = data.translation;
        subtitleTranslation.style.opacity = '1';
        setTimeout(() => {
            subtitleTranslation.scrollTop = subtitleTranslation.scrollHeight;
        }, 0);
    } else if (!data.is_partial) {
        subtitleTranslation.style.opacity = '0';
    }
}

connect();
