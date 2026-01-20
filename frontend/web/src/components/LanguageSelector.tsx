// src/components/LanguageSelector.tsx
import { useState } from 'react';

interface LanguageSelectorProps {
  onLanguageChange: (lang: string) => void;
  disabled?: boolean;
}

export default function LanguageSelector({ onLanguageChange, disabled }: LanguageSelectorProps) {
  const [selected, setSelected] = useState('en');

  const languages = [
    { code: 'en', name: 'English' },
    { code: 'yo', name: 'Yoruba (Coming Soon)' },
    { code: 'ig', name: 'Igbo (Coming Soon)' },
    { code: 'ha', name: 'Hausa (Coming Soon)' },
    { code: 'pcm', name: 'Pidgin (Coming Soon)' },
  ];

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const lang = e.target.value;
    setSelected(lang);
    onLanguageChange(lang);
  };

  return (
    <div className="language-selector-container">
      <select value={selected} onChange={handleChange} disabled={disabled}>
        {languages.map(l => (
          <option key={l.code} value={l.code} disabled={l.name.includes('Coming Soon')}>
            {l.name}
          </option>
        ))}
      </select>

      {/* Styles moved to parent container */}
      <style>{`
        .language-selector-container {
          display: flex;
          align-items: center;
          justify-content: flex-start;
          margin-left: 1rem; /* space from buttons */
        }

        .language-selector-container select {
          padding: 0.6rem 0.8rem;       /* comfortable vertical padding */
          border-radius: 10px;
          border: 2px solid #1B3B6F;   /* dark-blue border */
          background: #0D1321;          /* dark background to match app */
          color: #fff;                  /* white text */
          font-weight: 500;
          font-size: 0.95rem;
          cursor: pointer;
          width: 100px;                 /* shorter left-to-right width */
          transition: all 0.2s ease;
        }

        .language-selector-container select:hover {
          border-color: #576574;
          background: #1B3B6F;
        }

        .language-selector-container select:focus {
          outline: none;
          box-shadow: 0 0 0 3px rgba(88, 101, 116, 0.2);
        }



      `}</style>
    </div>
  );
}
