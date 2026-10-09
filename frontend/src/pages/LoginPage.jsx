import React, { useState } from 'react';
import { loginCustomer, registerCustomer } from '../services/api';

export default function LoginPage({ onAuthSuccess }) {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isRegister) {
        await registerCustomer(name, email, phone, password);
        // After dynamic registration, dynamically authenticate
        const loginData = await loginCustomer(email, password);
        onAuthSuccess(loginData.access_token, loginData.customer);
      } else {
        const loginData = await loginCustomer(email, password);
        onAuthSuccess(loginData.access_token, loginData.customer);
      }
    } catch (err) {
      setError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      maxWidth: '440px',
      margin: '60px auto',
      padding: '32px',
      backgroundColor: '#ffffff',
      borderRadius: '12px',
      boxShadow: '0 4px 20px rgba(0, 0, 0, 0.08)',
      border: '1px solid #e2e8f0'
    }}>
      <div style={{ textAlign: 'center', marginBottom: '24px' }}>
        <h2 style={{ margin: '0 0 8px 0', color: '#0f172a', fontSize: '24px' }}>
          {isRegister ? 'Create Customer Account' : 'Customer Portal Login'}
        </h2>
        <p style={{ margin: 0, color: '#64748b', fontSize: '14px' }}>
          {isRegister
            ? 'Sign up to access AI-powered customer support'
            : 'Sign in to access support and manage your requests'}
        </p>
      </div>

      {error && (
        <div style={{
          padding: '10px 14px',
          marginBottom: '16px',
          backgroundColor: '#fef2f2',
          border: '1px solid #fecaca',
          borderRadius: '6px',
          color: '#b91c1c',
          fontSize: '13px'
        }}>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {isRegister && (
          <>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, color: '#334155', marginBottom: '4px' }}>
                Full Name
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Enter your full name"
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  borderRadius: '6px',
                  border: '1px solid #cbd5e1',
                  fontSize: '14px',
                  boxSizing: 'border-box'
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, color: '#334155', marginBottom: '4px' }}>
                Phone Number
              </label>
              <input
                type="tel"
                required
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="Enter phone number"
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  borderRadius: '6px',
                  border: '1px solid #cbd5e1',
                  fontSize: '14px',
                  boxSizing: 'border-box'
                }}
              />
            </div>
          </>
        )}

        <div>
          <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, color: '#334155', marginBottom: '4px' }}>
            Email Address
          </label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="name@example.com"
            style={{
              width: '100%',
              padding: '10px 12px',
              borderRadius: '6px',
              border: '1px solid #cbd5e1',
              fontSize: '14px',
              boxSizing: 'border-box'
            }}
          />
        </div>

        <div>
          <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, color: '#334155', marginBottom: '4px' }}>
            Password
          </label>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            style={{
              width: '100%',
              padding: '10px 12px',
              borderRadius: '6px',
              border: '1px solid #cbd5e1',
              fontSize: '14px',
              boxSizing: 'border-box'
            }}
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          style={{
            marginTop: '8px',
            padding: '11px',
            backgroundColor: '#2563eb',
            color: '#ffffff',
            border: 'none',
            borderRadius: '6px',
            fontWeight: 600,
            fontSize: '14px',
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.7 : 1,
            transition: 'background-color 0.2s'
          }}
        >
          {loading ? 'Please wait...' : isRegister ? 'Register & Sign In' : 'Sign In'}
        </button>
      </form>

      <div style={{ marginTop: '18px', textAlign: 'center', fontSize: '13px', color: '#64748b' }}>
        {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
        <button
          type="button"
          onClick={() => {
            setIsRegister(!isRegister);
            setError('');
          }}
          style={{
            background: 'none',
            border: 'none',
            color: '#2563eb',
            fontWeight: 600,
            cursor: 'pointer',
            padding: 0
          }}
        >
          {isRegister ? 'Sign In' : 'Register Here'}
        </button>
      </div>

      {/* Demo helper card for interview / portfolio evaluators */}
      <div style={{
        marginTop: '24px',
        padding: '14px',
        backgroundColor: '#f8fafc',
        borderRadius: '8px',
        border: '1px dashed #cbd5e1',
        fontSize: '12px',
        color: '#475569'
      }}>
        <div style={{ fontWeight: 600, color: '#1e293b', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span>💡</span> <span>Evaluator & Interview Demo Credentials</span>
        </div>
        <p style={{ margin: '0 0 4px 0' }}>
          <strong>Seeded Account:</strong> <code style={{ backgroundColor: '#e2e8f0', padding: '1px 5px', borderRadius: '4px' }}>pushpak.bajanghate@example.com</code>
        </p>
        <p style={{ margin: '0 0 6px 0' }}>
          <strong>Password:</strong> <code style={{ backgroundColor: '#e2e8f0', padding: '1px 5px', borderRadius: '4px' }}>password123</code>
        </p>
        <p style={{ margin: 0, color: '#64748b', fontSize: '11px' }}>
          Or register any new customer account dynamically. The system maintains strict customer data isolation.
        </p>
      </div>
    </div>
  );
}
