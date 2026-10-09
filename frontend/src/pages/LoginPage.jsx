import { useState } from 'react';
import { loginCustomer, registerCustomer } from '../services/api';

export default function LoginPage({ onAuthSuccess }) {
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({ name: '', phone: '', email: '', password: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const isRegister = mode === 'register';

  const updateField = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }));

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    if (isRegister && (!form.name.trim() || !form.phone.trim())) {
      setError('Please enter your name and phone number.');
      return;
    }
    if (form.password.length < 6) {
      setError('Password must contain at least 6 characters.');
      return;
    }

    setLoading(true);
    try {
      if (isRegister) {
        await registerCustomer(form.name.trim(), form.email.trim(), form.phone.trim(), form.password);
      }
      const session = await loginCustomer(form.email.trim(), form.password);
      onAuthSuccess(session.access_token, session.customer);
    } catch (requestError) {
      setError(requestError.message || 'We could not sign you in. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const switchMode = () => {
    setMode((current) => (current === 'login' ? 'register' : 'login'));
    setError('');
  };

  return (
    <main className="auth-shell">
      <section className="auth-intro" aria-label="SupportAI introduction">
        <div className="brand-mark">S</div>
        <p className="eyebrow">SupportAI</p>
        <h1>Support that understands your order history.</h1>
        <p className="auth-intro-copy">Ask about orders, deliveries, returns, refunds, and policies in one secure conversation.</p>
        <div className="auth-capabilities" aria-label="Available support areas">
          <span>Orders</span><span>Returns</span><span>Refunds</span><span>Policies</span>
        </div>
      </section>

      <section className="auth-panel">
        <div className="auth-card">
          <div className="mobile-brand"><div className="brand-mark">S</div><span>SupportAI</span></div>
          <p className="eyebrow">{isRegister ? 'Create account' : 'Welcome back'}</p>
          <h2>{isRegister ? 'Set up your support account' : 'Sign in to SupportAI'}</h2>
          <p className="auth-subtitle">{isRegister ? 'Use your details to create a secure customer account.' : 'Your conversations and account data stay private.'}</p>

          <form className="auth-form" onSubmit={handleSubmit} noValidate>
            {isRegister && <>
              <label>Full name<input value={form.name} onChange={updateField('name')} autoComplete="name" required minLength="2" /></label>
              <label>Phone number<input value={form.phone} onChange={updateField('phone')} autoComplete="tel" required minLength="7" /></label>
            </>}
            <label>Email address<input type="email" value={form.email} onChange={updateField('email')} autoComplete="email" required /></label>
            <label>
              Password
              <span className="password-field">
                <input type={showPassword ? 'text' : 'password'} value={form.password} onChange={updateField('password')} autoComplete={isRegister ? 'new-password' : 'current-password'} required minLength="6" />
                <button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? 'Hide password' : 'Show password'}>{showPassword ? 'Hide' : 'Show'}</button>
              </span>
            </label>
            {error && <p className="form-error" role="alert">{error}</p>}
            <button className="primary-button" type="submit" disabled={loading}>{loading ? 'Please wait…' : isRegister ? 'Create account' : 'Sign in'}</button>
          </form>

          <p className="auth-switch">{isRegister ? 'Already have an account?' : 'New to SupportAI?'} <button type="button" onClick={switchMode}>{isRegister ? 'Sign in' : 'Create an account'}</button></p>
        </div>
      </section>
    </main>
  );
}
