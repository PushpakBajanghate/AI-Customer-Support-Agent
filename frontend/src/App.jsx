import { useEffect, useState } from 'react';
import ChatPage from './pages/ChatPage';
import LoginPage from './pages/LoginPage';
import { getCurrentCustomer } from './services/api';

const TOKEN_KEY = 'token';
const CUSTOMER_KEY = 'customer';

function readStoredCustomer() {
  try {
    const value = localStorage.getItem(CUSTOMER_KEY);
    return value ? JSON.parse(value) : null;
  } catch {
    localStorage.removeItem(CUSTOMER_KEY);
    return null;
  }
}

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) || '');
  const [customer, setCustomer] = useState(readStoredCustomer);
  const [checkingSession, setCheckingSession] = useState(Boolean(localStorage.getItem(TOKEN_KEY)));
  const [chatKey, setChatKey] = useState(0);

  useEffect(() => {
    if (!token) {
      setCheckingSession(false);
      return;
    }

    let active = true;
    getCurrentCustomer(token)
      .then((profile) => {
        if (!active) return;
        setCustomer(profile);
        localStorage.setItem(CUSTOMER_KEY, JSON.stringify(profile));
      })
      .catch(() => {
        if (!active) return;
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(CUSTOMER_KEY);
        setToken('');
        setCustomer(null);
      })
      .finally(() => active && setCheckingSession(false));

    return () => {
      active = false;
    };
  }, [token]);

  const handleAuthenticated = (accessToken, profile) => {
    localStorage.setItem(TOKEN_KEY, accessToken);
    localStorage.setItem(CUSTOMER_KEY, JSON.stringify(profile));
    setToken(accessToken);
    setCustomer(profile);
    setChatKey((value) => value + 1);
  };

  const handleLogout = () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(CUSTOMER_KEY);
    setToken('');
    setCustomer(null);
  };

  if (checkingSession) {
    return <div className="app-loading" role="status">Restoring your secure session…</div>;
  }

  if (!token || !customer) {
    return <LoginPage onAuthSuccess={handleAuthenticated} />;
  }

  return (
    <ChatPage
      key={chatKey}
      token={token}
      customer={customer}
      onLogout={handleLogout}
      onNewChat={() => setChatKey((value) => value + 1)}
    />
  );
}
