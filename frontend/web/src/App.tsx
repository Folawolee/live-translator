import React, { useEffect, useRef, useState } from "react";

export default function App() {
  const socketRef = useRef<WebSocket | null>(null);
  const [status, setStatus] = useState("Disconnected");
  const [subtitle, setSubtitle] = useState("Waiting...");

  const connect = () => {
    const ws = new WebSocket("ws://localhost:8000/ws");
    socketRef.current = ws;

    ws.onopen = () => {
      setStatus("Connected");
      console.log("WS connected");

      // 🔹 Send test message
      ws.send(new Float32Array([0, 0, 0]).buffer);
    };

    ws.onmessage = (event) => {
      console.log("Received:", event.data);
      setSubtitle(event.data);
    };

    ws.onerror = (err) => {
      console.error("WS error", err);
      setStatus("Error");
    };

    ws.onclose = () => {
      setStatus("Disconnected");
    };
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#121212",
        color: "#fff",
        padding: 40,
        fontFamily: "sans-serif",
      }}
    >
      <h1>Live Translator – Web MVP</h1>

      <p>Status: <strong>{status}</strong></p>

      <div
        style={{
          background: "#000",
          padding: 24,
          fontSize: "2rem",
          minHeight: 120,
          marginTop: 20,
          borderRadius: 8,
        }}
      >
        {subtitle}
      </div>

      <button
        onClick={connect}
        style={{
          marginTop: 30,
          padding: "12px 24px",
          fontSize: "1rem",
        }}
      >
        Connect to Backend
      </button>
    </div>
  );
}
