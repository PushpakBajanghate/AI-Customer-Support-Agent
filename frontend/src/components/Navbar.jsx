import React from 'react';

export default function Navbar({ customer, onLogout }) {
  return (
    <header style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '12px 24px',
      backgroundColor: '#ffffff',
      borderBottom: '1px solid #e2e8f0',
      boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div style={{
          width: '32px',
          height: '32px',
          borderRadius: '8px',
          backgroundColor: '#2563eb',
          color: '#ffffff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 'bold',
          fontSize: '16px'
        }}>
          AI
        </div>
        <div>
          <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 600, color: '#0f172a' }}>
            Customer Support
          </h2>
          <span style={{ fontSize: '12px', color: '#64748b' }}>Phase 3: Interactive Chat UI</span>
        </div>
      </div>

      {customer && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ textAlign: 'right', fontSize: '13px' }}>
            <div style={{ fontWeight: 600, color: '#1e293b' }}>{customer.name}</div>
            <div style={{ color: '#64748b', fontSize: '12px' }}>ID #{customer.id} &bull; {customer.email}</div>
          </div>
          <button
            onClick={onLogout}
            style={{
              padding: '6px 14px',
              fontSize: '13px',
              fontWeight: 500,
              backgroundColor: '#f1f5f9',
              color: '#334155',
              border: '1px solid #cbd5e1',
              borderRadius: '6px',
              cursor: 'pointer',
              transition: 'all 0.2s'
            }}
            onMouseOver={(e) => e.target.style.backgroundColor = '#e2e8f0'}
            onMouseOut={(e) => e.target.style.backgroundColor = '#f1f5f9'}
          >
            Sign Out
          </button>
        </div>
      )}
    </header>
  );
}
