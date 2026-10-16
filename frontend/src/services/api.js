/**
 * API service helper for backend communication.
 */
// Vercel builds replace VITE_API_URL at build time. Keep a production fallback
// so a missing Vercel variable never makes the deployed browser call localhost.
const configuredApiUrl = typeof import.meta !== 'undefined' && import.meta.env
  ? import.meta.env.VITE_API_URL
  : '';
const API_BASE_URL = (configuredApiUrl || (
  typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1'
    ? 'https://ai-customer-support-api-4le6.onrender.com'
    : 'http://localhost:8000'
)).replace(/\/$/, '');

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, options);
  } catch {
    throw new Error(`Cannot reach the support API at ${API_BASE_URL}. Check the backend deployment and VITE_API_URL.`);
  }

  const contentType = response.headers.get('content-type') || '';
  const data = contentType.includes('application/json')
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const detail = typeof data === 'object' ? data.detail : data;
    throw new Error(detail || `Request failed with status ${response.status}`);
  }
  return data;
}

export async function checkHealth() {
  return request('/health');
}

export async function loginCustomer(email, password) {
  return request('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
}

export async function registerCustomer(name, email, phone, password) {
  return request('/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, phone, password }),
  });
}

export async function getCurrentCustomer(token) {
  return request('/auth/me', {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
}

export async function sendChatMessage(message, token, conversationId = null) {
  return request('/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });
}

export async function fetchCustomerContext(token) {
  return request('/auth/context', {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
}

export async function fetchDemoCustomers() {
  return request('/auth/demo-customers');
}

export async function quickLoginDemo(customerId) {
  return request(`/auth/demo-login/${customerId}`, {
    method: 'POST',
  });
}
