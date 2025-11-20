let ws = null;
let reconnectInterval = null;
const subtitleOriginal = document.getElementById('subtitle-original');
const subtitleTranslation = document.getElementById('subtitle-translation');

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
    } else if (!data.is_partial) {
        subtitleOriginal.style.opacity = '0';
    }
    
    if (data.translation && data.translation.trim()) {
        subtitleTranslation.textContent = data.translation;
        subtitleTranslation.style.opacity = '1';
    } else if (!data.is_partial) {
        subtitleTranslation.style.opacity = '0';
    }
}

connect();
