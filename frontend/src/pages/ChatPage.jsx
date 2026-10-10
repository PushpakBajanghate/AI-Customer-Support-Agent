import { useEffect, useRef, useState } from 'react';
import {
  sendChatMessage,
  fetchCustomerContext,
  fetchDemoCustomers,
  quickLoginDemo,
} from '../services/api';
import ThemeToggle from '../components/ThemeToggle';

const defaultSuggestions = [
  { label: 'Track an order', text: 'Where is my order right now?' },
  { label: 'View my orders', text: 'What orders do I have on my account?' },
  { label: 'Cancel processing order', text: 'I want to cancel my order.' },
  { label: 'Return an item', text: 'How do I start a return for my delivered product?' },
  { label: 'Return policy', text: 'What is your store return and refund policy?' },
];

function messageId() {
  return globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`;
}

function formatTime(timestamp) {
  return new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(timestamp);
}

function MessageText({ children }) {
  return String(children)
    .split('\n')
    .map((line, index, arr) => (
      <span key={`${line}-${index}`}>
        {line}
        {index < arr.length - 1 && <br />}
      </span>
    ));
}

export default function ChatPage({ token, customer, onLogout, onNewChat, theme, onToggleTheme }) {
  const [messages, setMessages] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [failedMessage, setFailedMessage] = useState(null);
  const [customerContext, setCustomerContext] = useState(null);
  const [demoCustomers, setDemoCustomers] = useState([]);
  const [showSwitchModal, setShowSwitchModal] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const endRef = useRef(null);
  const textareaRef = useRef(null);

  // Load live customer orders and context from PostgreSQL
  useEffect(() => {
    if (!token) return;
    fetchCustomerContext(token)
      .then((data) => setCustomerContext(data))
      .catch((err) => console.warn('Could not fetch customer context:', err));

    fetchDemoCustomers()
      .then((data) => setDemoCustomers(data || []))
      .catch(() => {});
  }, [token]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const submitMessage = async (rawMessage, { appendUser = true } = {}) => {
    const content = rawMessage.trim();
    if (!content || loading) return;

    setError('');
    setFailedMessage(null);
    if (appendUser) {
      setMessages((current) => [
        ...current,
        { id: messageId(), role: 'user', content, timestamp: new Date() },
      ]);
    }
    setLoading(true);

    try {
      const response = await sendChatMessage(content, token, conversationId);
      setConversationId(response.conversation_id);
      setMessages((current) => [
        ...current,
        {
          id: messageId(),
          role: 'assistant',
          content: response.response,
          router: response.router,
          timestamp: new Date(response.timestamp || Date.now()),
        },
      ]);
      setInputText('');
      // Refresh customer context in case an order was cancelled or returned
      fetchCustomerContext(token)
        .then((data) => setCustomerContext(data))
        .catch(() => {});
    } catch (requestError) {
      setFailedMessage(content);
      setInputText(content);
      setError(requestError.message || 'We could not reach the support service. Please retry.');
    } finally {
      setLoading(false);
      requestAnimationFrame(() => textareaRef.current?.focus());
    }
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    const isRetry = failedMessage && failedMessage === inputText.trim();
    submitMessage(inputText, { appendUser: !isRetry });
  };

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSubmit(event);
    }
  };

  const startNewChat = () => {
    setConversationId(null);
    setMessages([]);
    setInputText('');
    setError('');
    setFailedMessage(null);
    onNewChat();
  };

  const handleSwitchCustomer = async (newCustomerId) => {
    try {
      const session = await quickLoginDemo(newCustomerId);
      setShowSwitchModal(false);
      localStorage.setItem('token', session.access_token);
      localStorage.setItem('customer', JSON.stringify(session.customer));
      window.location.reload();
    } catch (err) {
      alert('Failed to switch customer: ' + err.message);
    }
  };

  const orders = customerContext?.recent_orders || [];
  const shipments = customerContext?.shipments || [];

  return (
    <main className="workspace-shell">
      {/* Mobile Menu Button */}
      <button
        className="mobile-menu-button"
        type="button"
        onClick={() => setSidebarOpen(!sidebarOpen)}
        aria-label="Toggle navigation"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="3" y1="12" x2="21" y2="12" />
          <line x1="3" y1="6" x2="21" y2="6" />
          <line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>

      {/* Main Sidebar */}
      <aside className={`workspace-sidebar ${sidebarOpen ? 'is-open' : ''}`}>
        <div className="sidebar-brand">
          <div className="brand-mark">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M12 2a10 10 0 1 0 10 10H12V2z" />
              <path d="M12 12 2.1 7.1" />
              <path d="m12 12 5 9" />
            </svg>
          </div>
          <div className="sidebar-brand-text">
            <strong>SupportAI</strong>
            <span>Enterprise Multi-Agent</span>
          </div>
          <button
            type="button"
            className="sidebar-close-btn"
            onClick={() => setSidebarOpen(false)}
          >
            ✕
          </button>
        </div>

        <button type="button" className="sidebar-new-chat-btn" onClick={startNewChat}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          New Support Session
        </button>

        {/* Live Customer Orders Drawer */}
        <div className="sidebar-orders-section">
          <div className="sidebar-section-header">
            <span className="sidebar-section-title">Your Live Orders (PostgreSQL)</span>
            <span className="orders-count-badge">{orders.length}</span>
          </div>

          <div className="sidebar-orders-list">
            {orders.length === 0 ? (
              <div className="sidebar-no-orders">
                No orders found on this profile.
              </div>
            ) : (
              orders.map((o) => {
                const ship = shipments.find((s) => s.order_id === o.id);
                const itemsStr = (o.items || []).map((it) => it.product_name).join(', ') || 'Item';
                return (
                  <div key={o.id} className="sidebar-order-card">
                    <div className="order-card-top">
                      <strong className="order-id-label">Order #{o.id}</strong>
                      <span className={`status-pill status-${o.status.toLowerCase()}`}>
                        {o.status.toUpperCase()}
                      </span>
                    </div>
                    <p className="order-product-name" title={itemsStr}>
                      {itemsStr}
                    </p>
                    {ship && (
                      <div className="order-shipment-line">
                        <span className="carrier-badge">{ship.carrier}</span>
                        <span className="tracking-code">{ship.tracking_number}</span>
                      </div>
                    )}
                    <div className="order-card-actions">
                      <button
                        type="button"
                        className="order-action-btn"
                        onClick={() => submitMessage(`Where is my order #${o.id}?`)}
                      >
                        Track
                      </button>
                      {o.status.toLowerCase() === 'processing' && (
                        <button
                          type="button"
                          className="order-action-btn btn-danger"
                          onClick={() => submitMessage(`I want to cancel order #${o.id}.`)}
                        >
                          Cancel
                        </button>
                      )}
                      {o.status.toLowerCase() === 'delivered' && (
                        <button
                          type="button"
                          className="order-action-btn btn-return"
                          onClick={() => submitMessage(`I want to return item from order #${o.id}.`)}
                        >
                          Return
                        </button>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        <div className="sidebar-spacer" />

        {/* Switch Customer Profile Drawer Button */}
        <button
          type="button"
          className="switch-profile-btn"
          onClick={() => setShowSwitchModal(true)}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
            <circle cx="9" cy="7" r="4" />
            <polyline points="16 11 18 13 22 9" />
          </svg>
          Switch Demo Customer
        </button>

        {/* User Card */}
        <div className="sidebar-user-card">
          <div className="user-avatar-circle">
            {customer.name?.slice(0, 1).toUpperCase()}
          </div>
          <div className="user-info-text">
            <strong>{customer.name}</strong>
            <span title={customer.email}>{customer.email}</span>
          </div>
          <button
            type="button"
            className="sidebar-logout-icon"
            onClick={onLogout}
            title="Log Out"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
          </button>
        </div>
      </aside>

      {sidebarOpen && (
        <div className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Main Chat Workspace */}
      <section className="chat-workspace">
        {/* Top Header */}
        <header className="chat-workspace-header">
          <div className="header-left">
            <h1>Autonomous Support Agent</h1>
            <p className="header-sub">
              Multi-Agent LangGraph • Grounded in PostgreSQL & Store Policies
            </p>
          </div>
          <div className="header-right">
            {onToggleTheme && <ThemeToggle theme={theme} onToggle={onToggleTheme} />}
            <div className="connection-status-pill">
              <span className="pulse-dot" />
              <span>Real-Time Model Connected</span>
            </div>
          </div>
        </header>

        {/* Chat Scroll Container */}
        <div className="chat-scroll-area">
          {messages.length === 0 ? (
            <div className="chat-welcome-hero">
              <div className="hero-orb">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
              </div>
              <h2>How can SupportAI assist you, {customer.name?.split(' ')[0]}?</h2>
              <p>
                Ask about your active shipments, cancel an order, start a return, or inquire about company warranty policies.
              </p>

              <div className="welcome-quick-chips">
                {defaultSuggestions.map((item) => (
                  <button
                    key={item.label}
                    type="button"
                    className="welcome-chip"
                    onClick={() => submitMessage(item.text)}
                    disabled={loading}
                  >
                    <span>{item.label}</span>
                    <span className="chip-arrow">→</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="chat-messages-stream">
              {messages.map((message) => {
                const isUser = message.role === 'user';
                return (
                  <article
                    key={message.id}
                    className={`message-bubble-row ${isUser ? 'is-user' : 'is-assistant'}`}
                  >
                    {!isUser && (
                      <div className="assistant-avatar-badge">
                        <span>AI</span>
                      </div>
                    )}
                    <div className="message-content-wrapper">
                      <div className="message-meta-header">
                        <strong>{isUser ? 'You' : 'SupportAI Agent'}</strong>
                        <time>{formatTime(message.timestamp)}</time>
                      </div>

                      <div className="message-text-bubble">
                        <MessageText>{message.content}</MessageText>
                      </div>

                      {/* Decagon-style Intent Tag */}
                      {!isUser && message.router && (
                        <div className="decagon-intent-tag">
                          <span className="intent-dot" />
                          <span className="intent-name">
                            {message.router.intent?.replaceAll('_', ' ')}
                          </span>
                          {typeof message.router.confidence === 'number' && (
                            <span className="intent-conf">
                              • {Math.round(message.router.confidence * 100)}% Match
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </article>
                );
              })}

              {loading && (
                <div className="assistant-thinking-indicator">
                  <div className="thinking-dots">
                    <span />
                    <span />
                    <span />
                  </div>
                  <span className="thinking-label">
                    SupportAI is retrieving database records and reasoning with Gemini...
                  </span>
                </div>
              )}
              <div ref={endRef} />
            </div>
          )}
        </div>

        {error && (
          <div className="chat-error-bar" role="alert">
            <span className="error-text">{error}</span>
            <div className="error-actions">
              <button
                type="button"
                className="retry-btn"
                onClick={() => submitMessage(failedMessage || inputText, { appendUser: false })}
                disabled={!failedMessage || loading}
              >
                Retry
              </button>
              <button
                type="button"
                className="dismiss-btn"
                onClick={() => setError('')}
              >
                ✕
              </button>
            </div>
          </div>
        )}

        {/* Floating Message Composer */}
        <div className="composer-shell">
          <form className="composer-form" onSubmit={handleSubmit}>
            <textarea
              ref={textareaRef}
              className="composer-textarea"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about orders, tracking, returns, cancellations, or store policies..."
              rows={1}
              disabled={loading}
            />
            <button
              type="submit"
              className="composer-send-btn"
              disabled={loading || !inputText.trim()}
              title="Send Message"
            >
              {loading ? (
                <span className="spinner-send" />
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              )}
            </button>
          </form>
          <div className="composer-shortcuts">
            <span>Press <kbd>Enter</kbd> to send · <kbd>Shift + Enter</kbd> for new line</span>
          </div>
        </div>
      </section>

      {/* Switch Demo Customer Modal */}
      {showSwitchModal && (
        <div className="modal-overlay" onClick={() => setShowSwitchModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Switch Customer Profile</h3>
              <button type="button" className="modal-close" onClick={() => setShowSwitchModal(false)}>
                ✕
              </button>
            </div>
            <p className="modal-subtitle">
              Select any demo customer to instantly inspect their distinct orders, shipments, and permissions:
            </p>
            <div className="modal-customer-list">
              {demoCustomers.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  className={`modal-customer-btn ${c.id === customer.id ? 'is-active' : ''}`}
                  onClick={() => handleSwitchCustomer(c.id)}
                >
                  <div className="modal-avatar">{c.name.slice(0, 1).toUpperCase()}</div>
                  <div className="modal-details">
                    <strong>{c.name}</strong>
                    <span>{c.email}</span>
                  </div>
                  {c.id === customer.id && <span className="active-tag">Current</span>}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
