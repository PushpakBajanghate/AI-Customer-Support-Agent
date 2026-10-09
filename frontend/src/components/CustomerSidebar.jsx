import React, { useState, useEffect } from 'react';
import { fetchCustomerContext, fetchDemoCustomers, quickLoginDemo } from '../services/api';

export default function CustomerSidebar({ token, currentCustomer, onSwitchCustomer, onQuickPrompt }) {
  const [contextData, setContextData] = useState(null);
  const [customersList, setCustomersList] = useState([]);
  const [loadingContext, setLoadingContext] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  // Load demo customer list on mount
  useEffect(() => {
    fetchDemoCustomers()
      .then((data) => setCustomersList(data || []))
      .catch((err) => console.warn('Could not load customer personas:', err));
  }, []);

  // Load customer relational context whenever token/customer changes
  useEffect(() => {
    if (!token) return;
    setLoadingContext(true);
    fetchCustomerContext(token)
      .then((data) => setContextData(data))
      .catch((err) => console.warn('Could not load customer context:', err))
      .finally(() => setLoadingContext(false));
  }, [token, currentCustomer]);

  const handleSelectCustomer = async (e) => {
    const selectedId = Number(e.target.value);
    if (!selectedId || selectedId === currentCustomer?.id) return;
    try {
      const authData = await quickLoginDemo(selectedId);
      onSwitchCustomer(authData.access_token, authData.customer);
    } catch (err) {
      console.error('Failed to switch customer:', err);
    }
  };

  const orders = contextData?.recent_orders || [];
  const returns = contextData?.open_returns || [];
  const tickets = contextData?.open_support_tickets || [];

  const getStatusBadge = (status) => {
    const s = (status || '').toLowerCase();
    let bg = '#f1f5f9';
    let color = '#475569';
    let border = '#cbd5e1';

    if (s === 'delivered') {
      bg = '#ecfdf5';
      color = '#047857';
      border = '#a7f3d0';
    } else if (s === 'shipped') {
      bg = '#eff6ff';
      color = '#1d4ed8';
      border = '#bfdbfe';
    } else if (s === 'processing' || s === 'requested') {
      bg = '#fffbeb';
      color = '#b45309';
      border = '#fde68a';
    } else if (s === 'cancelled') {
      bg = '#fef2f2';
      color = '#b91c1c';
      border = '#fecaca';
    }

    return (
      <span style={{
        fontSize: '11px',
        fontWeight: 600,
        padding: '2px 8px',
        borderRadius: '999px',
        backgroundColor: bg,
        color: color,
        border: `1px solid ${border}`,
        textTransform: 'uppercase',
        letterSpacing: '0.04em'
      }}>
        {status}
      </span>
    );
  };

  if (collapsed) {
    return (
      <div style={{
        width: '48px',
        backgroundColor: '#ffffff',
        borderRight: '1px solid #e2e8f0',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '16px 0',
        gap: '16px'
      }}>
        <button
          onClick={() => setCollapsed(false)}
          title="Expand Customer Profile & Orders"
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            fontSize: '18px',
            color: '#64748b'
          }}
        >
          ➡️
        </button>
      </div>
    );
  }

  return (
    <aside style={{
      width: '340px',
      backgroundColor: '#ffffff',
      borderRight: '1px solid #e2e8f0',
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      overflowY: 'auto',
      boxSizing: 'border-box'
    }}>
      {/* Top Header & Switcher */}
      <div style={{
        padding: '16px 20px',
        borderBottom: '1px solid #f1f5f9',
        backgroundColor: '#fafbfc'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{
              display: 'inline-block',
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: '#10b981',
              boxShadow: '0 0 0 2px #d1fae5'
            }} />
            <span style={{ fontSize: '11px', fontWeight: 700, color: '#047857', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
              Verified Customer
            </span>
          </div>
          <button
            onClick={() => setCollapsed(true)}
            title="Collapse Sidebar"
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: '14px',
              color: '#94a3b8'
            }}
          >
            ◀
          </button>
        </div>

        {/* Customer Profile Card */}
        <div style={{
          backgroundColor: '#ffffff',
          border: '1px solid #e2e8f0',
          borderRadius: '10px',
          padding: '12px 14px',
          boxShadow: '0 1px 2px rgba(0,0,0,0.03)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              backgroundColor: '#e0e7ff',
              color: '#4338ca',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 700,
              fontSize: '14px'
            }}>
              {currentCustomer?.name ? currentCustomer.name.charAt(0) : 'U'}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                fontWeight: 700,
                fontSize: '14px',
                color: '#0f172a',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
              }}>
                {currentCustomer?.name || 'Customer'}
              </div>
              <div style={{
                fontSize: '11px',
                color: '#64748b',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
              }}>
                {currentCustomer?.email}
              </div>
            </div>
          </div>

          <div style={{
            fontSize: '11px',
            color: '#64748b',
            display: 'flex',
            justifyContent: 'space-between',
            paddingTop: '6px',
            borderTop: '1px solid #f1f5f9'
          }}>
            <span>Customer ID: <strong>#{currentCustomer?.id}</strong></span>
            <span>Phone: <strong>{currentCustomer?.phone || 'N/A'}</strong></span>
          </div>
        </div>

        {/* Persona Switcher Dropdown */}
        <div style={{ marginTop: '12px' }}>
          <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
            Switch Customer Persona (Multi-Tenant Demo):
          </label>
          <select
            value={currentCustomer?.id || 1}
            onChange={handleSelectCustomer}
            style={{
              width: '100%',
              padding: '7px 10px',
              fontSize: '12px',
              borderRadius: '6px',
              border: '1px solid #cbd5e1',
              backgroundColor: '#ffffff',
              color: '#1e293b',
              cursor: 'pointer',
              outline: 'none'
            }}
          >
            {customersList.map((c) => (
              <option key={c.id} value={c.id}>
                #{c.id} {c.name} ({c.email})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Orders Section */}
      <div style={{ flex: 1, padding: '16px 20px', overflowY: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <span style={{ fontSize: '12px', fontWeight: 700, color: '#334155', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Recent Orders ({orders.length})
          </span>
          {loadingContext && (
            <span style={{ fontSize: '11px', color: '#3b82f6' }}>Refreshing...</span>
          )}
        </div>

        {orders.length === 0 ? (
          <div style={{
            padding: '24px 16px',
            textAlign: 'center',
            backgroundColor: '#f8fafc',
            borderRadius: '8px',
            border: '1px dashed #cbd5e1',
            color: '#64748b',
            fontSize: '12px'
          }}>
            No recent orders found for this customer.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {orders.map((order) => {
              const orderStatus = (order.status || '').toLowerCase();
              return (
                <div
                  key={order.id}
                  style={{
                    backgroundColor: '#ffffff',
                    border: '1px solid #e2e8f0',
                    borderRadius: '8px',
                    padding: '12px',
                    transition: 'box-shadow 0.15s',
                    boxShadow: '0 1px 2px rgba(0,0,0,0.03)'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <span style={{ fontWeight: 700, fontSize: '13px', color: '#0f172a' }}>
                      Order #{order.id}
                    </span>
                    {getStatusBadge(order.status)}
                  </div>

                  <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '6px' }}>
                    {order.order_date ? new Date(order.order_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : 'Recent'} &bull; ₹{order.total_amount?.toLocaleString() || '0'}
                  </div>

                  {order.items && order.items.length > 0 && (
                    <div style={{
                      fontSize: '12px',
                      color: '#334155',
                      backgroundColor: '#f8fafc',
                      padding: '6px 8px',
                      borderRadius: '4px',
                      marginBottom: '8px'
                    }}>
                      {order.items.map((item, idx) => (
                        <div key={idx} style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          • {item.product_name} (x{item.quantity})
                        </div>
                      ))}
                    </div>
                  )}

                  {/* 1-Click Interactive Action Buttons */}
                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    <button
                      type="button"
                      onClick={() => onQuickPrompt(`Where is my order #${order.id}? Can you give me tracking updates?`)}
                      style={{
                        padding: '4px 8px',
                        fontSize: '11px',
                        fontWeight: 600,
                        backgroundColor: '#eff6ff',
                        color: '#1d4ed8',
                        border: '1px solid #bfdbfe',
                        borderRadius: '4px',
                        cursor: 'pointer'
                      }}
                    >
                      📦 Track
                    </button>

                    {orderStatus === 'processing' && (
                      <button
                        type="button"
                        onClick={() => onQuickPrompt(`I want to cancel order #${order.id}. Please proceed.`)}
                        style={{
                          padding: '4px 8px',
                          fontSize: '11px',
                          fontWeight: 600,
                          backgroundColor: '#fef2f2',
                          color: '#b91c1c',
                          border: '1px solid #fecaca',
                          borderRadius: '4px',
                          cursor: 'pointer'
                        }}
                      >
                        ❌ Cancel
                      </button>
                    )}

                    {orderStatus === 'delivered' && (
                      <button
                        type="button"
                        onClick={() => onQuickPrompt(`I would like to initiate a return for items in order #${order.id}.`)}
                        style={{
                          padding: '4px 8px',
                          fontSize: '11px',
                          fontWeight: 600,
                          backgroundColor: '#fefce8',
                          color: '#854d0e',
                          border: '1px solid #fef08a',
                          borderRadius: '4px',
                          cursor: 'pointer'
                        }}
                      >
                        🔄 Return
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Open Returns & Tickets if any */}
        {(returns.length > 0 || tickets.length > 0) && (
          <div style={{ marginTop: '18px' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Active Inquiries ({returns.length + tickets.length})
            </span>
            <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {returns.map((ret) => (
                <div key={ret.id} style={{
                  padding: '8px 10px',
                  backgroundColor: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                  fontSize: '11px',
                  color: '#475569'
                }}>
                  <div style={{ fontWeight: 600, color: '#0f172a', display: 'flex', justifyContent: 'space-between' }}>
                    <span>Return #{ret.id} (Order #{ret.order_id})</span>
                    <span style={{ color: '#b45309' }}>{ret.status}</span>
                  </div>
                  <div style={{ marginTop: '2px', color: '#64748b' }}>{ret.reason}</div>
                </div>
              ))}
              {tickets.slice(0, 2).map((t) => (
                <div key={t.id} style={{
                  padding: '8px 10px',
                  backgroundColor: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                  fontSize: '11px',
                  color: '#475569'
                }}>
                  <div style={{ fontWeight: 600, color: '#0f172a', display: 'flex', justifyContent: 'space-between' }}>
                    <span>Ticket #{t.id}</span>
                    <span style={{ color: '#2563eb' }}>{t.status}</span>
                  </div>
                  <div style={{ marginTop: '2px', color: '#64748b' }}>{t.subject || t.summary}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Quick Knowledge Actions */}
        <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid #f1f5f9' }}>
          <span style={{ fontSize: '11px', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Store Policy Questions
          </span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '8px' }}>
            <button
              type="button"
              onClick={() => onQuickPrompt('What is your return policy? How many days do I have?')}
              style={{
                textAlign: 'left',
                padding: '6px 10px',
                fontSize: '12px',
                backgroundColor: '#ffffff',
                border: '1px solid #e2e8f0',
                borderRadius: '6px',
                color: '#334155',
                cursor: 'pointer'
              }}
            >
              📋 Return Policy (30 Days)
            </button>
            <button
              type="button"
              onClick={() => onQuickPrompt('How long does standard delivery take?')}
              style={{
                textAlign: 'left',
                padding: '6px 10px',
                fontSize: '12px',
                backgroundColor: '#ffffff',
                border: '1px solid #e2e8f0',
                borderRadius: '6px',
                color: '#334155',
                cursor: 'pointer'
              }}
            >
              🚚 Shipping & Delivery Times
            </button>
            <button
              type="button"
              onClick={() => onQuickPrompt('When and how are refunds processed?')}
              style={{
                textAlign: 'left',
                padding: '6px 10px',
                fontSize: '12px',
                backgroundColor: '#ffffff',
                border: '1px solid #e2e8f0',
                borderRadius: '6px',
                color: '#334155',
                cursor: 'pointer'
              }}
            >
              💳 Refund Timelines & Methods
            </button>
          </div>
        </div>
      </div>
    </aside>
  );
}
