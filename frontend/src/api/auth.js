const BACKEND_BASE = '/backend-api'

async function parseResponse(res) {
  let data = null
  try {
    data = await res.json()
  } catch {
    data = null
  }
  if (!res.ok) {
    const message = data?.message || `Request failed: ${res.status}`
    throw new Error(message)
  }
  return data
}

const AUTH_REQUEST_TIMEOUT_MS = 10_000

async function request(path, init = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), AUTH_REQUEST_TIMEOUT_MS)
  try {
    const res = await fetch(`${BACKEND_BASE}${path}`, {
      credentials: 'include',
      ...init,
      signal: controller.signal,
    })
    return parseResponse(res)
  } catch (err) {
    if (err?.name === 'AbortError') {
      throw new Error('后端响应超时，请检查 8010 服务或数据库连接')
    }
    throw err
  } finally {
    clearTimeout(timer)
  }
}

export function fetchMe() {
  return request('/api/auth/me')
}

export function loginWithPassword(email, password) {
  return request('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
}

export function logoutCurrentSession() {
  return request('/api/auth/logout', { method: 'POST' })
}

export function sendRegisterCode(email) {
  return request('/api/auth/register/send-code', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })
}

export function verifyRegisterCode(email, code) {
  return request('/api/auth/register/verify-code', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, code }),
  })
}

export function completeRegister(email, displayName, password, verificationToken) {
  return request('/api/auth/register/complete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email,
      display_name: displayName,
      password,
      verification_token: verificationToken,
    }),
  })
}

export function sendPasswordResetCode(email) {
  return request('/api/auth/password-reset/send-code', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })
}

export function verifyPasswordResetCode(email, code) {
  return request('/api/auth/password-reset/verify-code', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, code }),
  })
}

export function completePasswordReset(email, newPassword, verificationToken) {
  return request('/api/auth/password-reset/complete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email,
      new_password: newPassword,
      verification_token: verificationToken,
    }),
  })
}
