import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import LoginPage from './pages/LoginPage';
import ChatPage from './pages/ChatPage';
import { getCurrentCustomer } from './services/api';

function App() {
  const [token, setToken] = useState(() => localStorage.getItem('token') || '');
  const [customer, setCustomer] = useState(() => {
    const cached = localStorage.getItem('customer');
    return cached ? JSON.parse(cached) : null;
  });
  const [validating, setValidating] = useState(false);

  useEffect(() => {
    if (token && !customer) {
      setValidating(true);
      getCurrentCustomer(token)
        .then((userData) => {
          setCustomer(userData);
          localStorage.setItem('customer', JSON.stringify(userData));
        })
        .catch(() => {
          // Token expired or invalid
          setToken('');
          setCustomer(null);
          localStorage.removeItem('token');
          localStorage.removeItem('customer');
        })
        .finally(() => setValidating(false));
    }
  }, [token, customer]);

  const handleAuthSuccess = (newToken, newCustomer) => {
    setToken(newToken);
    setCustomer(newCustomer);
    localStorage.setItem('token', newToken);
    localStorage.setItem('customer', JSON.stringify(newCustomer));
  };

  const handleLogout = () => {
    setToken('');
    setCustomer(null);
    localStorage.removeItem('token');
    localStorage.removeItem('customer');
  };

  if (validating) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        color: '#64748b',
        fontSize: '16px'
      }}>
        Authenticating session...
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f1f5f9', display: 'flex', flexDirection: 'column' }}>
      <Navbar customer={customer} onLogout={handleLogout} />
      <main style={{ flex: 1, padding: '16px', boxSizing: 'border-box' }}>
        {token && customer ? (
          <ChatPage token={token} customer={customer} />
        ) : (
          <LoginPage onAuthSuccess={handleAuthSuccess} />
        )}
      </main>
    </div>
  );
}

export default App;
