import React from 'react';

export default function Navbar({ customer, onLogout, onNewChat }) {
  return (
    <header style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '14px 28px',
      backgroundColor: '#ffffff',
      borderBottom: '1px solid #e2e8f0',
      boxShadow: '0 1px 3px rgba(0,0,0,0.04)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{
          width: '36px',
          height: '36px',
          borderRadius: '10px',
          background: 'linear-gradient(135deg, #2563eb, #1d4ed8)',
          color: '#ffffff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 700,
          fontSize: '15px',
          boxShadow: '0 2px 8px rgba(37,99,235,0.25)'
        }}>
          AI
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 style={{ margin: 0, fontSize: '17px', fontWeight: 700, color: '#0f172a', letterSpacing: '-0.01em' }}>
              Autonomous Customer Support
            </h1>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '2px 8px',
              borderRadius: '999px',
              fontSize: '11px',
              fontWeight: 600,
              backgroundColor: '#ecfdf5',
              color: '#047857',
              border: '1px solid #a7f3d0'
            }}>
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#10b981' }} />
              Live System
            </span>
          </div>
          <span style={{ fontSize: '12px', color: '#64748b' }}>
            LangGraph Multi-Agent Architecture • Real-Time RAG & PostgreSQL
          </span>
        </div>
      </div>

      {customer && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          {onNewChat && (
            <button
              onClick={onNewChat}
              style={{
                padding: '7px 13px',
                fontSize: '12px',
                fontWeight: 600,
                backgroundColor: '#f8fafc',
                color: '#334155',
                border: '1px solid #cbd5e1',
                borderRadius: '6px',
                cursor: 'pointer',
                transition: 'all 0.15s'
              }}
              onMouseOver={(e) => { e.currentTarget.style.backgroundColor = '#f1f5f9'; }}
              onMouseOut={(e) => { e.currentTarget.style.backgroundColor = '#f8fafc'; }}
            >
              + New Chat
            </button>
          )}
          <div style={{ textAlign: 'right', fontSize: '13px' }}>
            <div style={{ fontWeight: 600, color: '#0f172a' }}>{customer.name}</div>
            <div style={{ color: '#64748b', fontSize: '11px' }}>
              Customer #{customer.id} &bull; {customer.email}
            </div>
          </div>
          <button
            onClick={onLogout}
            style={{
              padding: '7px 14px',
              fontSize: '12px',
              fontWeight: 600,
              backgroundColor: '#ffffff',
              color: '#ef4444',
              border: '1px solid #fecaca',
              borderRadius: '6px',
              cursor: 'pointer',
              transition: 'all 0.15s'
            }}
            onMouseOver={(e) => { e.currentTarget.style.backgroundColor = '#fef2f2'; }}
            onMouseOut={(e) => { e.currentTarget.style.backgroundColor = '#ffffff'; }}
          >
            Sign Out
          </button>
        </div>
      )}
    </header>
  );
}
