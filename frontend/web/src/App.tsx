// src/App.tsx
import { useState, useRef } from 'react';
import SubtitleBox from './components/SubtitleBox';
import LanguageSelector from './components/LanguageSelector';
import logo from './assets/logo.png'; // or logo.svg

function App() {
  const [status, setStatus] = useState<string>('Ready');
  const [transcript, setTranscript] = useState<string>('');
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [selectedLanguage, setSelectedLanguage] = useState<string>('en');

  const wsRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);


  /** Connect or reconnect WebSocket */
  const connectWebSocket = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket('ws://127.0.0.1:8000/ws');

    ws.onopen = () => {
      setStatus('Connected');
      // Send current language on connect
      ws.send(JSON.stringify({ type: 'set_language', language: selectedLanguage }));
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'transcription') {
          setTranscript(prev => (prev ? prev + '\n' : '') + data.text);
        } else if (data.type === 'status') {
          setStatus(data.message);
        }
      } catch {
        setStatus(event.data);
      }
    };

    ws.onerror = () => setStatus('Connection error');
    ws.onclose = () => setStatus('Disconnected');

    wsRef.current = ws;
  };

  /** Handle language changes */
  const handleLanguageChange = (lang: string) => {
    setSelectedLanguage(lang);
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'set_language', language: lang }));
    }
  };

  /** Start recording audio and sending to WS */
  const startRecording = async () => {
  setIsRecording(true);
  setStatus('Recording...');

  connectWebSocket();

  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  streamRef.current = stream;

  const AudioContextClass =
    window.AudioContext || (window as any).webkitAudioContext;

  const audioContext = new AudioContextClass({ sampleRate: 16000 });
  audioContextRef.current = audioContext;

  // IMPORTANT: load worklet
  await audioContext.audioWorklet.addModule(
    new URL('./audio-processor.ts', import.meta.url)
  );

  const source = audioContext.createMediaStreamSource(stream);
  sourceRef.current = source;

  const workletNode = new AudioWorkletNode(audioContext, 'audio-processor');
  workletNodeRef.current = workletNode;

  workletNode.port.onmessage = (event) => {
    const inputData = event.data as Float32Array;

    const buffer = new ArrayBuffer(inputData.length * 4);
    const view = new DataView(buffer);

    for (let i = 0; i < inputData.length; i++) {
      view.setFloat32(i * 4, inputData[i], true);
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(buffer);
    }
  };

  source.connect(workletNode);
};


  /** Stop recording and close everything */
  const stopRecording = () => {
  setIsRecording(false);
  setStatus('Stopped');

  streamRef.current?.getTracks().forEach(track => track.stop());
  sourceRef.current?.disconnect();
  workletNodeRef.current?.disconnect();
  audioContextRef.current?.close();

  wsRef.current?.close();

  streamRef.current = null;
  sourceRef.current = null;
  workletNodeRef.current = null;
  audioContextRef.current = null;
  wsRef.current = null;
};


  return (
    <div className="app-container">
      <header className="header">
        <div className="logo-container">
          <img src={logo} alt="VoxBridge Logo" className="logo-img" />
        </div>
      </header>

      <div className="status-bar">{status}</div>

      <SubtitleBox transcript={transcript} />

      <div className="controls">
        <div className="button-group">
          <button onClick={startRecording} disabled={isRecording}>Start Listening</button>
          <button onClick={stopRecording} disabled={!isRecording}>Stop</button>
        </div>
        <div className="language-selector-wrapper">
          <LanguageSelector
            onLanguageChange={handleLanguageChange}
            disabled={isRecording}
          />
        </div>
      </div>

      {/* Styling kept intact */}
      <style>{`
        * { box-sizing: border-box; margin: 0; padding: 0; }

        .app-container {
          min-height: 100vh;
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 2rem;
          font-family: 'Segoe UI', system-ui, sans-serif;
          background: #0D1321;
          color: #FFF;
        }

        .header { text-align: center; margin-bottom: 2rem; }

        .logo-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.5rem;
        }

        .logo-img { width: 300px; height: auto; margin-bottom: 1rem; }

        .status-bar {
          background: rgba(255,255,255,0.05);
          padding: 0.75rem 2rem;
          border-radius: 12px;
          margin-bottom: 1.5rem;
          min-width: 350px;
          text-align: center;
          font-weight: 500;
        }

        .controls {
          display: flex;
          align-items: center;
          gap: 1.5rem;
          margin-top: 1.5rem;
          flex-wrap: wrap;
          justify-content: center;
        }

        .button-group { display: flex; gap: 1rem; }
        .button-group button {
          padding: 0.75rem 2.2rem;
          border-radius: 12px;
          border: none;
          cursor: pointer;
          font-weight: 600;
          font-size: 1rem;
          transition: transform 0.2s ease, background 0.3s ease;
          color: #fff;
          min-width: 140px;
        }
        .button-group button:hover:not(:disabled) { transform: translateY(-2px); }
        .button-group button:disabled { opacity: 0.6; cursor: not-allowed; }
        .button-group button:first-child { background: #1B3B6F; }
        .button-group button:last-child { background: #576574; }

        .language-selector-wrapper { min-width: 150px; }

        .subtitle-container { width: 90%; max-width: 1100px; margin-bottom: 1.5rem; }

        @media (max-width: 768px) {
          .controls { flex-direction: column; gap: 1rem; }
          .subtitle-container { width: 95%; }
        }
      `}</style>
    </div>
  );
}

export default App;
