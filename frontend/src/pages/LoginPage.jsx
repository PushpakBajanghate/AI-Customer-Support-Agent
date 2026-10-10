import { useEffect, useState } from 'react';
import { loginCustomer, registerCustomer, fetchDemoCustomers, quickLoginDemo } from '../services/api';
import ThemeToggle from '../components/ThemeToggle';

export default function LoginPage({ onAuthSuccess, theme, onToggleTheme }) {
  const [tab, setTab] = useState('demo'); // 'demo' | 'login' | 'register'
  const [demoCustomers, setDemoCustomers] = useState([]);
  const [form, setForm] = useState({ name: '', phone: '', email: '', password: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchDemoCustomers()
      .then((customers) => setDemoCustomers(customers || []))
      .catch((err) => console.warn('Could not prefetch demo customers:', err));
  }, []);

  const updateField = (field) => (event) => {
    setForm((current) => ({ ...current, [field]: event.target.value }));
  };

  const handleDemoLogin = async (customerId) => {
    setError('');
    setLoading(true);
    try {
      const session = await quickLoginDemo(customerId);
      onAuthSuccess(session.access_token, session.customer);
    } catch (err) {
      setError(err.message || 'Failed to switch demo profile.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    const isRegister = tab === 'register';

    if (isRegister && (!form.name.trim() || !form.phone.trim())) {
      setError('Please provide your full name and phone number.');
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
      setError(requestError.message || 'Authentication failed. Please verify your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="auth-shell">
      <section className="auth-intro">
        <div>
          <div className="brand">
            <div className="brand-mark">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2a10 10 0 1 0 10 10H12V2z" />
                <path d="M12 12 2.1 7.1" />
                <path d="m12 12 5 9" />
              </svg>
            </div>
            <span>SupportAI Enterprise</span>
          </div>

          <div className="auth-copy">
            <p className="eyebrow">Production AI Customer Support</p>
            <h1>Real-Time Autonomous Support Grounded in Live Data</h1>
            <p>
              Connects directly to PostgreSQL transactional records and LangGraph state machines.
              Grounds order lookups, tracking, returns, and safety gates in real-time.
            </p>
          </div>
        </div>

        <div className="auth-benefits">
          <div className="auth-benefit">
            <strong>PostgreSQL Grounded</strong>
            <span>Verified order & shipment records</span>
          </div>
          <div className="auth-benefit">
            <strong>Supervisor Gate</strong>
            <span>Safe order cancellation & returns</span>
          </div>
          <div className="auth-benefit">
            <strong>Hybrid Policy RAG</strong>
            <span>Instant policy citations & warranty rules</span>
          </div>
          <div className="auth-benefit">
            <strong>Google Gemini LLM</strong>
            <span>Dynamic, real-time reasoning</span>
          </div>
        </div>
      </section>

      <section className="auth-panel">
        <div className="auth-card">
          <div className="auth-header-top">
            <span className="auth-badge">Secure Customer Portal</span>
            {onToggleTheme && <ThemeToggle theme={theme} onToggle={onToggleTheme} />}
          </div>
          <div className="auth-header-block">
            <h2>Sign in to SupportAI</h2>
            <p className="auth-subtitle">
              Select a pre-loaded customer profile with active orders or use your account credentials.
            </p>
          </div>

          <div className="auth-tabs">
            <button
              type="button"
              className={`auth-tab ${tab === 'demo' ? 'is-active' : ''}`}
              onClick={() => { setTab('demo'); setError(''); }}
            >
              Demo Profiles
            </button>
            <button
              type="button"
              className={`auth-tab ${tab === 'login' ? 'is-active' : ''}`}
              onClick={() => { setTab('login'); setError(''); }}
            >
              Sign In
            </button>
            <button
              type="button"
              className={`auth-tab ${tab === 'register' ? 'is-active' : ''}`}
              onClick={() => { setTab('register'); setError(''); }}
            >
              New Account
            </button>
          </div>

          {error && <div className="form-error" role="alert">{error}</div>}

          {tab === 'demo' && (
            <div className="demo-profiles-container">
              <p className="demo-profiles-hint">
                Click any profile to immediately explore live orders, tracking numbers, and returns:
              </p>
              <div className="demo-profiles-list">
                {demoCustomers.length === 0 ? (
                  <div className="demo-loading">Loading customer profiles...</div>
                ) : (
                  demoCustomers.map((cust) => (
                    <button
                      key={cust.id}
                      type="button"
                      className="demo-customer-item"
                      disabled={loading}
                      onClick={() => handleDemoLogin(cust.id)}
                    >
                      <div className="demo-customer-avatar">
                        {cust.name.slice(0, 1).toUpperCase()}
                      </div>
                      <div className="demo-customer-info">
                        <strong>{cust.name}</strong>
                        <span>{cust.email}</span>
                      </div>
                      <span className="demo-arrow">→</span>
                    </button>
                  ))
                )}
              </div>
            </div>
          )}

          {tab !== 'demo' && (
            <form className="auth-form" onSubmit={handleSubmit} noValidate>
              {tab === 'register' && (
                <>
                  <div className="field-group">
                    <label>Full Name</label>
                    <input
                      type="text"
                      className="field-input"
                      value={form.name}
                      onChange={updateField('name')}
                      placeholder="e.g. Pushpak Bajanghate"
                      required
                    />
                  </div>
                  <div className="field-group">
                    <label>Phone Number</label>
                    <input
                      type="tel"
                      className="field-input"
                      value={form.phone}
                      onChange={updateField('phone')}
                      placeholder="+91-9876543210"
                      required
                    />
                  </div>
                </>
              )}

              <div className="field-group">
                <label>Email Address</label>
                <input
                  type="email"
                  className="field-input"
                  value={form.email}
                  onChange={updateField('email')}
                  placeholder="name@example.com"
                  required
                />
              </div>

              <div className="field-group">
                <label>Password</label>
                <div className="password-input-wrapper">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    className="field-input"
                    value={form.password}
                    onChange={updateField('password')}
                    placeholder="••••••••"
                    required
                    minLength={6}
                  />
                  <button
                    type="button"
                    className="password-toggle-btn"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? 'Hide' : 'Show'}
                  </button>
                </div>
              </div>

              <button className="primary-button" type="submit" disabled={loading}>
                {loading ? 'Authenticating...' : tab === 'register' ? 'Create Account & Start' : 'Sign In'}
              </button>
            </form>
          )}

          <div className="auth-footer-note">
            <span className="dot-live" /> All conversations are protected with JWT HS256 tokens and tenant isolation.
          </div>
        </div>
      </section>
    </main>
  );
}
