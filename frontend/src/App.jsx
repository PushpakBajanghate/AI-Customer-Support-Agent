import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import LoginPage from './pages/LoginPage';
import ChatPage from './pages/ChatPage';
import { getCurrentCustomer, quickLoginDemo } from './services/api';

function App() {
  const [token, setToken] = useState(() => localStorage.getItem('token') || '');
  const [customer, setCustomer] = useState(() => {
    const cached = localStorage.getItem('customer');
    return cached ? JSON.parse(cached) : null;
  });
  const [loading, setLoading] = useState(false);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [chatSessionKey, setChatSessionKey] = useState(0);

  // Auto-authenticate default customer if no active session, so user NEVER sees a dead blocker screen
  useEffect(() => {
    if (!token || !customer) {
      setLoading(true);
      quickLoginDemo(1)
        .then((authData) => {
          setToken(authData.access_token);
          setCustomer(authData.customer);
          localStorage.setItem('token', authData.access_token);
          localStorage.setItem('customer', JSON.stringify(authData.customer));
        })
        .catch((err) => {
          console.warn('Auto-login fallback:', err);
        })
        .finally(() => setLoading(false));
    } else {
      // Validate existing token
      getCurrentCustomer(token)
        .then((userData) => {
          setCustomer(userData);
          localStorage.setItem('customer', JSON.stringify(userData));
        })
        .catch(() => {
          // Token expired, re-login as customer 1
          quickLoginDemo(1).then((authData) => {
            setToken(authData.access_token);
            setCustomer(authData.customer);
            localStorage.setItem('token', authData.access_token);
            localStorage.setItem('customer', JSON.stringify(authData.customer));
          });
        });
    }
  }, []);

  const handleCustomerSwitch = (newToken, newCustomer) => {
    setToken(newToken);
    setCustomer(newCustomer);
    localStorage.setItem('token', newToken);
    localStorage.setItem('customer', JSON.stringify(newCustomer));
    setChatSessionKey((prev) => prev + 1);
  };

  const handleAuthSuccess = (newToken, newCustomer) => {
    handleCustomerSwitch(newToken, newCustomer);
    setShowAuthModal(false);
  };

  const handleLogout = () => {
    // When signing out, switch back to guest/switch persona rather than showing a dead screen
    setShowAuthModal(true);
  };

  if (loading && !customer) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        backgroundColor: '#f8fafc',
        gap: '12px'
      }}>
        <div style={{
          width: '32px',
          height: '32px',
          border: '3px solid #e2e8f0',
          borderTopColor: '#2563eb',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite'
        }} />
        <div style={{ color: '#475569', fontSize: '14px', fontWeight: 500 }}>
          Initializing AI Customer Support Agent Workspace...
        </div>
      </div>
    );
  }

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden', backgroundColor: '#f1f5f9' }}>
      <Navbar
        customer={customer}
        onLogout={() => setShowAuthModal(true)}
        onNewChat={() => setChatSessionKey((k) => k + 1)}
      />

      <main style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}>
        <ChatPage
          key={chatSessionKey}
          token={token}
          customer={customer}
          onSwitchCustomer={handleCustomerSwitch}
        />

        {/* Optional Manual Login Modal */}
        {showAuthModal && (
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.65)',
            backdropFilter: 'blur(4px)',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px'
          }}>
            <div style={{
              position: 'relative',
              width: '100%',
              maxWidth: '460px',
              backgroundColor: '#ffffff',
              borderRadius: '16px',
              boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
              overflow: 'hidden'
            }}>
              <button
                onClick={() => setShowAuthModal(false)}
                style={{
                  position: 'absolute',
                  top: '16px',
                  right: '16px',
                  background: 'none',
                  border: 'none',
                  fontSize: '20px',
                  color: '#64748b',
                  cursor: 'pointer',
                  zIndex: 10
                }}
              >
                ✕
              </button>
              <div style={{ padding: '8px' }}>
                <LoginPage onAuthSuccess={handleAuthSuccess} />
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
