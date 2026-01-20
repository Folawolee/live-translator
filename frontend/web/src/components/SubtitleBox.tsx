// src/components/SubtitleBox.tsx
import { useRef, useEffect } from 'react';

interface SubtitleBoxProps {
  transcript: string;
}

export default function SubtitleBox({ transcript }: SubtitleBoxProps) {
  const outputRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (outputRef.current) outputRef.current.scrollTop = outputRef.current.scrollHeight;
  }, [transcript]);

  return (
    <div className="subtitle-container">
      <div ref={outputRef} className="transcript-content">
        {transcript ? transcript.split('\n').map((line, idx) => (
          <p key={idx} className="line">{line}</p>
        )) : <p className="placeholder">Waiting for speech...</p>}
      </div>

      <style>{`
        .subtitle-container {
          width: 90%;
          max-width: 1200px;
          margin-bottom: 2rem;
        }

        .transcript-content {
          background: #19192c;
          color: #FFFFFF;
          min-height: 500px;
          max-height: 65vh;
          padding: 1.5rem;
          border-radius: 20px;
          overflow-y: auto;
          font-size: 1.1rem;
          line-height: 1.6;
          box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }

        .line { margin-bottom: 0.75rem; }

        .placeholder {
          color: #FFFFFF;
          font-style: italic;
          font-size: 1.3rem;  /* slightly larger for the taller box */
          text-align: center;
          line-height: 1.6;
        }

      `}</style>
    </div>
  );
}
