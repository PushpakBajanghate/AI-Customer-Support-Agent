import { useEffect, useRef, useState } from 'react';
import { sendChatMessage } from '../services/api';

const suggestions = [
  { label: 'Track an order', text: 'Where is my order?' },
  { label: 'Start a return', text: 'I want to return an item.' },
  { label: 'Refund status', text: 'What is the status of my refund?' },
  { label: 'Return policy', text: 'What is your return policy?' },
];

function messageId() {
  return globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`;
}

function formatTime(timestamp) {
  return new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(timestamp);
}

function MessageText({ children }) {
  return String(children).split('\n').map((line, index) => (
    <span key={`${line}-${index}`}>{line}{index < String(children).split('\n').length - 1 && <br />}</span>
  ));
}

export default function ChatPage({ token, customer, onLogout, onNewChat }) {
  const [messages, setMessages] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [failedMessage, setFailedMessage] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const endRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const submitMessage = async (rawMessage, { appendUser = true } = {}) => {
    const content = rawMessage.trim();
    if (!content || loading) return;

    setError('');
    setFailedMessage(null);
    if (appendUser) {
      setMessages((current) => [...current, { id: messageId(), role: 'user', content, timestamp: new Date() }]);
    }
    setLoading(true);

    try {
      const response = await sendChatMessage(content, token, conversationId);
      setConversationId(response.conversation_id);
      setMessages((current) => [...current, {
        id: messageId(),
        role: 'assistant',
        content: response.response,
        router: response.router,
        timestamp: new Date(response.timestamp || Date.now()),
      }]);
      setInputText('');
    } catch (requestError) {
      setFailedMessage(content);
      setInputText(content);
      setError(requestError.message || 'We could not reach the support service. Your message is still ready to retry.');
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

  return (
    <main className="workspace-shell">
      <button className="mobile-menu-button" type="button" onClick={() => setSidebarOpen(true)} aria-label="Open navigation">Menu</button>
      <aside className={`workspace-sidebar ${sidebarOpen ? 'is-open' : ''}`} aria-label="SupportAI navigation">
        <div className="sidebar-brand"><div className="brand-mark">S</div><span>SupportAI</span><button type="button" className="sidebar-close" onClick={() => setSidebarOpen(false)} aria-label="Close navigation">×</button></div>
        <button type="button" className="new-chat-button" onClick={startNewChat}>+ New chat</button>
        <div className="sidebar-section">
          <p className="sidebar-label">Current session</p>
          <div className="session-card"><span className="session-dot" /> <span>{conversationId ? 'Conversation in progress' : 'New conversation'}</span></div>
        </div>
        <div className="sidebar-spacer" />
        <div className="account-card">
          <div className="avatar" aria-hidden="true">{customer.name?.slice(0, 1).toUpperCase()}</div>
          <div><strong>{customer.name}</strong><span>{customer.email}</span></div>
        </div>
        <button type="button" className="logout-button" onClick={onLogout}>Log out</button>
      </aside>
      {sidebarOpen && <button className="sidebar-backdrop" type="button" onClick={() => setSidebarOpen(false)} aria-label="Close navigation" />}

      <section className="chat-workspace">
        <header className="chat-header">
          <div><p className="eyebrow">AI customer support</p><h1>Support assistant</h1><p>Secure help for orders, returns, refunds, shipping, and policies.</p></div>
          <div className="secure-status"><span /> Authenticated</div>
        </header>

        <div className="chat-scroll" aria-live="polite">
          {messages.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">✦</div>
              <h2>How can we help you today?</h2>
              <p>Ask a question or tell your AI support assistant what you need help with.</p>
              <div className="suggestion-grid">
                {suggestions.map((item) => <button key={item.label} type="button" onClick={() => submitMessage(item.text)} disabled={loading}>{item.label}</button>)}
              </div>
            </div>
          ) : (
            <div className="message-list">
              {messages.map((message) => {
                const isUser = message.role === 'user';
                return <article className={`message-row ${isUser ? 'from-user' : 'from-assistant'}`} key={message.id}>
                  {!isUser && <div className="assistant-avatar" aria-hidden="true">S</div>}
                  <div className="message-content">
                    <div className="message-meta"><strong>{isUser ? 'You' : 'SupportAI'}</strong><span>{formatTime(message.timestamp)}</span></div>
                    <div className="message-bubble"><MessageText>{message.content}</MessageText></div>
                    {!isUser && message.router && <div className="intent-chip">{message.router.intent?.replaceAll('_', ' ').toLowerCase()} {typeof message.router.confidence === 'number' && <span>• {Math.round(message.router.confidence * 100)}%</span>}</div>}
                  </div>
                </article>;
              })}
              {loading && <div className="thinking" role="status"><span /><span /><span /> SupportAI is checking your request…</div>}
              <div ref={endRef} />
            </div>
          )}
        </div>

        {error && <div className="chat-error" role="alert"><span>{error}</span><div><button type="button" onClick={() => submitMessage(failedMessage || inputText, { appendUser: false })} disabled={!failedMessage || loading}>Retry</button><button type="button" onClick={() => setError('')} aria-label="Dismiss error">×</button></div></div>}

        <div className="composer-area">
          {messages.length > 0 && <div className="composer-suggestions">{suggestions.map((item) => <button key={item.label} type="button" onClick={() => submitMessage(item.text)} disabled={loading}>{item.label}</button>)}</div>}
          <form className="composer" onSubmit={handleSubmit}>
            <textarea ref={textareaRef} value={inputText} onChange={(event) => setInputText(event.target.value)} onKeyDown={handleKeyDown} placeholder="Message SupportAI…" rows="1" disabled={loading} aria-label="Message SupportAI" />
            <button type="submit" disabled={loading || !inputText.trim()}>{loading ? 'Sending…' : 'Send'}</button>
          </form>
          <p className="composer-hint">Enter to send · Shift + Enter for a new line</p>
        </div>
      </section>
    </main>
  );
}
