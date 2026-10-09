import React, { useState, useEffect, useRef } from 'react';
import CustomerSidebar from '../components/CustomerSidebar';
import { sendChatMessage } from '../services/api';

export default function ChatPage({ token, customer, onSwitchCustomer }) {
  const [messages, setMessages] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  // Initial welcome message tailored to current authenticated customer
  useEffect(() => {
    if (customer && messages.length === 0) {
      setMessages([
        {
          id: 'welcome-1',
          sender: 'assistant',
          text: `Hello ${customer.name}! 👋 Welcome to Customer Support. I have access to your account details and recent orders. How can I help you today?`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          router: {
            intent: 'GENERAL_QUESTION',
            confidence: 1.0,
            needs_clarification: false
          }
        }
      ]);
    }
  }, [customer]);

  const executeSend = async (messageText) => {
    const textToSend = (messageText || inputText).trim();
    if (!textToSend || loading) return;

    setError('');
    const userMsg = {
      id: Date.now(),
      sender: 'user',
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText('');
    setLoading(true);

    try {
      const data = await sendChatMessage(textToSend, token, conversationId);
      if (data.conversation_id) {
        setConversationId(data.conversation_id);
      }

      const assistantMsg = {
        id: Date.now() + 1,
        sender: 'assistant',
        text: data.response,
        router: data.router,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      console.error('Chat error:', err);
      setError(err.message || 'Failed to communicate with support agent.');
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    executeSend(inputText);
  };

  const handleQuickPrompt = (promptText) => {
    executeSend(promptText);
  };

  const handleResetChat = () => {
    setConversationId(null);
    setError('');
    setMessages([
      {
        id: Date.now(),
        sender: 'assistant',
        text: `Chat session refreshed. How can I help you today, ${customer?.name || 'there'}?`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        router: { intent: 'GENERAL_QUESTION', confidence: 1.0 }
      }
    ]);
  };

  return (
    <div style={{
      display: 'flex',
      width: '100%',
      height: '100%',
      backgroundColor: '#f8fafc',
      overflow: 'hidden'
    }}>
      {/* Left Column: Customer Context & Verification Hub */}
      <CustomerSidebar
        token={token}
        currentCustomer={customer}
        onSwitchCustomer={onSwitchCustomer}
        onQuickPrompt={handleQuickPrompt}
      />

      {/* Main Column: Live Agent Chat Workspace */}
      <section style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        backgroundColor: '#ffffff',
        position: 'relative',
        overflow: 'hidden'
      }}>
        {/* Chat Header */}
        <div style={{
          padding: '12px 24px',
          borderBottom: '1px solid #e2e8f0',
          backgroundColor: '#ffffff',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '12px',
              backgroundColor: '#eff6ff',
              border: '1px solid #bfdbfe',
              color: '#2563eb',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '20px'
            }}>
              🤖
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 style={{ margin: 0, fontSize: '15px', fontWeight: 700, color: '#0f172a' }}>
                  AI Support Specialist
                </h2>
                <span style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  padding: '2px 8px',
                  borderRadius: '999px',
                  backgroundColor: '#ecfdf5',
                  color: '#047857',
                  border: '1px solid #a7f3d0'
                }}>
                  ● Online
                </span>
              </div>
              <div style={{ fontSize: '12px', color: '#64748b' }}>
                Context-Aware &bull; Secure Multi-Tenant &bull; Customer #{customer?.id}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button
              type="button"
              onClick={handleResetChat}
              style={{
                padding: '6px 12px',
                fontSize: '12px',
                fontWeight: 600,
                backgroundColor: '#ffffff',
                color: '#475569',
                border: '1px solid #cbd5e1',
                borderRadius: '6px',
                cursor: 'pointer',
                transition: 'background 0.15s'
              }}
              onMouseOver={(e) => (e.currentTarget.style.backgroundColor = '#f1f5f9')}
              onMouseOut={(e) => (e.currentTarget.style.backgroundColor = '#ffffff')}
            >
              🔄 Clear Chat
            </button>
          </div>
        </div>

        {/* Real runtime error banner */}
        {error && (
          <div style={{
            padding: '10px 20px',
            backgroundColor: '#fef2f2',
            borderBottom: '1px solid #fecaca',
            color: '#b91c1c',
            fontSize: '13px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <span>⚠️ {error}</span>
            <button
              onClick={() => setError('')}
              style={{
                background: 'none',
                border: 'none',
                color: '#b91c1c',
                cursor: 'pointer',
                fontWeight: 'bold'
              }}
            >
              ✕
            </button>
          </div>
        )}

        {/* Message Thread */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
          backgroundColor: '#fafbfc'
        }}>
          {messages.map((msg) => {
            const isUser = msg.sender === 'user';
            return (
              <div
                key={msg.id}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: isUser ? 'flex-end' : 'flex-start',
                  maxWidth: '75%',
                  alignSelf: isUser ? 'flex-end' : 'flex-start'
                }}
              >
                {/* Sender badge & time */}
                <div style={{
                  fontSize: '11px',
                  color: '#94a3b8',
                  marginBottom: '4px',
                  paddingLeft: isUser ? 0 : '4px',
                  paddingRight: isUser ? '4px' : 0,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}>
                  <span style={{ fontWeight: 600, color: isUser ? '#1e293b' : '#2563eb' }}>
                    {isUser ? 'You' : 'AI Support Agent'}
                  </span>
                  <span>&bull;</span>
                  <span>{msg.timestamp}</span>
                </div>

                {/* Message Bubble */}
                <div style={{
                  padding: '13px 18px',
                  borderRadius: isUser ? '16px 16px 3px 16px' : '16px 16px 16px 3px',
                  backgroundColor: isUser ? '#2563eb' : '#ffffff',
                  color: isUser ? '#ffffff' : '#1e293b',
                  boxShadow: isUser ? '0 2px 4px rgba(37,99,235,0.2)' : '0 1px 3px rgba(0,0,0,0.06)',
                  border: isUser ? 'none' : '1px solid #e2e8f0',
                  fontSize: '14px',
                  lineHeight: '1.55',
                  wordBreak: 'break-word',
                  whiteSpace: 'pre-wrap'
                }}>
                  {msg.text}
                </div>

                {/* Router Intent Badge (Transparency feature) */}
                {!isUser && msg.router && msg.router.intent && (
                  <div style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    marginTop: '5px',
                    padding: '3px 10px',
                    borderRadius: '999px',
                    backgroundColor: '#ffffff',
                    border: '1px solid #e2e8f0',
                    fontSize: '11px',
                    color: '#64748b',
                    boxShadow: '0 1px 2px rgba(0,0,0,0.02)'
                  }}>
                    <span style={{
                      width: '6px',
                      height: '6px',
                      borderRadius: '50%',
                      backgroundColor: msg.router.intent === 'UNKNOWN' ? '#f59e0b' : '#10b981'
                    }} />
                    <span>Intent: <strong style={{ color: '#0f172a' }}>{msg.router.intent}</strong></span>
                    {msg.router.confidence && (
                      <span style={{ color: '#059669', fontWeight: 600 }}>
                        {Math.round(msg.router.confidence * 100)}% confidence
                      </span>
                    )}
                    {msg.router.needs_clarification && (
                      <span style={{ color: '#d97706', fontWeight: 600 }}>&bull; clarification needed</span>
                    )}
                  </div>
                )}
              </div>
            );
          })}

          {/* Typing indicator */}
          {loading && (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'flex-start',
              maxWidth: '75%',
              alignSelf: 'flex-start'
            }}>
              <div style={{ fontSize: '11px', color: '#94a3b8', marginBottom: '4px', paddingLeft: '4px' }}>
                AI Agent is analyzing context & querying database...
              </div>
              <div style={{
                padding: '12px 18px',
                borderRadius: '16px 16px 16px 3px',
                backgroundColor: '#ffffff',
                border: '1px solid #e2e8f0',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.04)'
              }}>
                <span className="typing-dot" style={{ width: '7px', height: '7px', borderRadius: '50%', backgroundColor: '#2563eb' }}></span>
                <span className="typing-dot" style={{ width: '7px', height: '7px', borderRadius: '50%', backgroundColor: '#60a5fa' }}></span>
                <span className="typing-dot" style={{ width: '7px', height: '7px', borderRadius: '50%', backgroundColor: '#93c5fd' }}></span>
                <span style={{ fontSize: '12px', color: '#64748b', marginLeft: '6px' }}>Thinking...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Quick Suggestion Pills */}
        <div style={{
          padding: '8px 24px',
          backgroundColor: '#fafbfc',
          borderTop: '1px solid #f1f5f9',
          display: 'flex',
          gap: '8px',
          overflowX: 'auto',
          whiteSpace: 'nowrap'
        }}>
          {[
            { label: '📦 Track Latest Order', prompt: 'Where is my latest order right now?' },
            { label: '❌ Cancel Processing Order', prompt: 'Can you cancel my processing order?' },
            { label: '🔄 Return Policy Window', prompt: 'What is your return policy and window?' },
            { label: '🎧 Product Information', prompt: 'Tell me about the AuraBass Earbuds specs and warranty.' },
            { label: '🧑‍💼 Speak to Human Agent', prompt: 'I want to speak to a human representative.' }
          ].map((pill, idx) => (
            <button
              key={idx}
              type="button"
              disabled={loading}
              onClick={() => handleQuickPrompt(pill.prompt)}
              style={{
                padding: '6px 12px',
                fontSize: '12px',
                borderRadius: '999px',
                backgroundColor: '#ffffff',
                border: '1px solid #cbd5e1',
                color: '#334155',
                cursor: loading ? 'not-allowed' : 'pointer',
                transition: 'all 0.15s',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px'
              }}
              onMouseOver={(e) => {
                if (!loading) {
                  e.currentTarget.style.backgroundColor = '#eff6ff';
                  e.currentTarget.style.borderColor = '#93c5fd';
                  e.currentTarget.style.color = '#1d4ed8';
                }
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.backgroundColor = '#ffffff';
                e.currentTarget.style.borderColor = '#cbd5e1';
                e.currentTarget.style.color = '#334155';
              }}
            >
              {pill.label}
            </button>
          ))}
        </div>

        {/* Input & Send Form */}
        <form
          onSubmit={handleSubmit}
          style={{
            display: 'flex',
            gap: '12px',
            padding: '16px 24px',
            backgroundColor: '#ffffff',
            borderTop: '1px solid #e2e8f0',
            alignItems: 'center'
          }}
        >
          <input
            ref={inputRef}
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Type your question or request (e.g. 'Where is my order #2?', 'I want to return an item')..."
            disabled={loading}
            style={{
              flex: 1,
              padding: '13px 18px',
              borderRadius: '10px',
              border: '1px solid #cbd5e1',
              fontSize: '14px',
              outline: 'none',
              boxSizing: 'border-box',
              transition: 'border-color 0.15s'
            }}
            onFocus={(e) => (e.target.style.borderColor = '#2563eb')}
            onBlur={(e) => (e.target.style.borderColor = '#cbd5e1')}
          />
          <button
            type="submit"
            disabled={loading || !inputText.trim()}
            style={{
              padding: '13px 26px',
              backgroundColor: inputText.trim() && !loading ? '#2563eb' : '#94a3b8',
              color: '#ffffff',
              border: 'none',
              borderRadius: '10px',
              fontWeight: 600,
              fontSize: '14px',
              cursor: inputText.trim() && !loading ? 'pointer' : 'not-allowed',
              transition: 'all 0.15s',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: inputText.trim() && !loading ? '0 2px 6px rgba(37,99,235,0.3)' : 'none'
            }}
          >
            <span>{loading ? 'Sending...' : 'Send'}</span>
            <span>➤</span>
          </button>
        </form>
      </section>
    </div>
  );
}
