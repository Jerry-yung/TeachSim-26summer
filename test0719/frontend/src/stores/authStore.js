import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { clearHistoryCache, primeHistorySessionsCache } from '@/api/ai.js'
import {
  completePasswordReset,
  completeRegister,
  fetchMe,
  loginWithPassword,
  logoutCurrentSession,
  sendPasswordResetCode,
  sendRegisterCode,
  verifyPasswordResetCode,
  verifyRegisterCode,
} from '@/api/auth.js'

const LEGACY_KEYS = ['teachsim_auth', 'teachsim_users', 'teachsim_token']

function normalizeUser(raw) {
  if (!raw) return null
  const displayName = raw.display_name || raw.name || raw.email?.split('@')[0] || '用户'
  return {
    ...raw,
    display_name: displayName,
    name: displayName,
  }
}

function purgeLegacyAuth() {
  for (const key of LEGACY_KEYS) {
    try {
      localStorage.removeItem(key)
    } catch {}
  }
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const initialized = ref(false)
  const initializing = ref(false)
  let initPromise = null

  const isLoggedIn = computed(() => !!user.value)
  const avatarChar = computed(() => {
    const seed = user.value?.display_name || user.value?.email || '?'
    return (seed.charAt(0) || '?').toUpperCase()
  })

  async function initialize(force = false) {
    if (initialized.value && !force) return user.value
    if (initPromise && !force) return initPromise

    initializing.value = true
    const timeoutMs = 12_000
    initPromise = Promise.race([
      (async () => {
        purgeLegacyAuth()
        try {
          const data = await fetchMe()
          user.value = normalizeUser(data.user)
          queueMicrotask(() => primeHistorySessionsCache({ limit: 50, offset: 0 }))
        } catch {
          user.value = null
          clearHistoryCache()
        }
        return user.value
      })(),
      new Promise((resolve) => {
        setTimeout(() => resolve(null), timeoutMs)
      }),
    ]).finally(() => {
      initialized.value = true
      initializing.value = false
      initPromise = null
    })

    return initPromise
  }

  async function login(email, password) {
    const data = await loginWithPassword(email, password)
    user.value = normalizeUser(data.user)
    initialized.value = true
    purgeLegacyAuth()
    clearHistoryCache()
    queueMicrotask(() => primeHistorySessionsCache({ limit: 50, offset: 0 }))
    return data
  }

  async function logout() {
    try {
      await logoutCurrentSession()
    } finally {
      user.value = null
      initialized.value = true
      clearHistoryCache()
      purgeLegacyAuth()
    }
  }

  async function refreshMe() {
    const data = await fetchMe()
    user.value = normalizeUser(data.user)
    initialized.value = true
    return data
  }

  async function sendRegisterCodeRequest(email) {
    return sendRegisterCode(email)
  }

  async function verifyRegisterCodeRequest(email, code) {
    return verifyRegisterCode(email, code)
  }

  async function completeRegisterRequest(email, displayName, password, verificationToken) {
    const data = await completeRegister(email, displayName, password, verificationToken)
    user.value = normalizeUser(data.user)
    initialized.value = true
    clearHistoryCache()
    purgeLegacyAuth()
    queueMicrotask(() => primeHistorySessionsCache({ limit: 50, offset: 0 }))
    return data
  }

  async function sendResetCodeRequest(email) {
    return sendPasswordResetCode(email)
  }

  async function verifyResetCodeRequest(email, code) {
    return verifyPasswordResetCode(email, code)
  }

  async function completeResetRequest(email, newPassword, verificationToken) {
    const data = await completePasswordReset(email, newPassword, verificationToken)
    user.value = normalizeUser(data.user)
    initialized.value = true
    clearHistoryCache()
    purgeLegacyAuth()
    queueMicrotask(() => primeHistorySessionsCache({ limit: 50, offset: 0 }))
    return data
  }

  return {
    user,
    initialized,
    initializing,
    isLoggedIn,
    avatarChar,
    initialize,
    refreshMe,
    login,
    logout,
    sendRegisterCode: sendRegisterCodeRequest,
    verifyRegisterCode: verifyRegisterCodeRequest,
    completeRegister: completeRegisterRequest,
    sendResetCode: sendResetCodeRequest,
    verifyResetCode: verifyResetCodeRequest,
    completeReset: completeResetRequest,
  }
})
