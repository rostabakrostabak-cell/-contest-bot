import { createRoot } from 'react-dom/client';
import App from './App';
import './index.css';

// Telegram WebApp ready
(window as unknown as { Telegram?: { WebApp?: { ready: () => void } } })
  .Telegram?.WebApp?.ready?.();

createRoot(document.getElementById('root')!).render(<App />);
