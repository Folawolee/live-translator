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
        .language-selector-container select {
          padding: 0.75rem 1rem;
          border-radius: 12px;
          border: 2px solid #f57c00;
          background: #fff;
          color: #333;
          font-weight: 500;
          cursor: pointer;
          min-width: 180px;
        }
        .language-selector-container select:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
        .language-selector-container select:hover:not(:disabled) {
          border-color: #d48806;
        }
      `}</style>
    </div>
  );
}
