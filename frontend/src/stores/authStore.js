import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const STORAGE_KEY = 'teachsim_auth'
const USERS_KEY = 'teachsim_users'

function loadUser() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function loadUsers() {
  try {
    const raw = localStorage.getItem(USERS_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveUsers(users) {
  localStorage.setItem(USERS_KEY, JSON.stringify(users))
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref(loadUser())

  const isLoggedIn = computed(() => !!user.value)

  // 头像首字
  const avatarChar = computed(() => {
    if (!user.value) return '?'
    return user.value.name.charAt(0)
  })

  function register(name, username, password, role = '实习教师') {
    const users = loadUsers()
    if (users.find(u => u.username === username)) {
      return { ok: false, msg: '该用户名已被注册' }
    }
    const newUser = { name, username, password, role }
    users.push(newUser)
    saveUsers(users)
    // 注册后不自动登录，需要用户手动登录
    return { ok: true }
  }

  function login(username, password) {
    const users = loadUsers()
    const found = users.find(u => u.username === username && u.password === password)
    if (!found) {
      return { ok: false, msg: '用户名或密码错误' }
    }
    user.value = { name: found.name, username: found.username, role: found.role }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(user.value))
    return { ok: true }
  }

  function logout() {
    user.value = null
    localStorage.removeItem(STORAGE_KEY)
  }

  return { user, isLoggedIn, avatarChar, register, login, logout }
})
