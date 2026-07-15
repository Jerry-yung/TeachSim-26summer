<template>
  <div class="login-page">

    <!-- ═══════════════════ GLOBAL DARK BACKGROUND ═══════════════════ -->
    <div class="global-bg">
      <div class="bg-grid"></div>
      <div class="glow g1"></div>
      <div class="glow g2"></div>
      <div class="glow g3"></div>
      <div class="glow g4"></div>
      <div class="scan-lines"></div>
    </div>

    <!-- ═══════════════════ LEFT PANEL ═══════════════════ -->
    <div class="left-panel">

      <!-- Neural network -->
      <svg class="neural-svg" viewBox="0 0 600 500" preserveAspectRatio="xMidYMid slice">
        <defs>
          <radialGradient id="node-cyan" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="#22D3EE" stop-opacity="0.9"/>
            <stop offset="100%" stop-color="#0891B2" stop-opacity="0.3"/>
          </radialGradient>
          <radialGradient id="node-purple" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="#A855F7" stop-opacity="0.9"/>
            <stop offset="100%" stop-color="#7C3AED" stop-opacity="0.3"/>
          </radialGradient>
          <filter id="glow-filter">
            <feGaussianBlur stdDeviation="3" result="blur"/>
            <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
        </defs>

        <!-- Edges -->
        <line class="edge" x1="60"  y1="120" x2="200" y2="80"/>
        <line class="edge" x1="60"  y1="120" x2="200" y2="180"/>
        <line class="edge" x1="60"  y1="240" x2="200" y2="80"/>
        <line class="edge" x1="60"  y1="240" x2="200" y2="180"/>
        <line class="edge" x1="60"  y1="240" x2="200" y2="280"/>
        <line class="edge" x1="60"  y1="360" x2="200" y2="180"/>
        <line class="edge" x1="60"  y1="360" x2="200" y2="280"/>
        <line class="edge" x1="200" y1="80"  x2="350" y2="140"/>
        <line class="edge" x1="200" y1="80"  x2="350" y2="240"/>
        <line class="edge" x1="200" y1="180" x2="350" y2="140"/>
        <line class="edge" x1="200" y1="180" x2="350" y2="240"/>
        <line class="edge" x1="200" y1="180" x2="350" y2="340"/>
        <line class="edge" x1="200" y1="280" x2="350" y2="240"/>
        <line class="edge" x1="200" y1="280" x2="350" y2="340"/>
        <line class="edge" x1="350" y1="140" x2="490" y2="180"/>
        <line class="edge" x1="350" y1="240" x2="490" y2="180"/>
        <line class="edge" x1="350" y1="240" x2="490" y2="300"/>
        <line class="edge" x1="350" y1="340" x2="490" y2="300"/>

        <!-- Nodes L1 -->
        <circle class="node nc" cx="60"  cy="120" r="9" filter="url(#glow-filter)"/>
        <circle class="node np" cx="60"  cy="240" r="9" filter="url(#glow-filter)"/>
        <circle class="node nc" cx="60"  cy="360" r="9" filter="url(#glow-filter)"/>
        <!-- Nodes L2 -->
        <circle class="node np" cx="200" cy="80"  r="11" filter="url(#glow-filter)"/>
        <circle class="node nc" cx="200" cy="180" r="13" filter="url(#glow-filter)"/>
        <circle class="node np" cx="200" cy="280" r="11" filter="url(#glow-filter)"/>
        <!-- Nodes L3 -->
        <circle class="node nc" cx="350" cy="140" r="11" filter="url(#glow-filter)"/>
        <circle class="node np" cx="350" cy="240" r="13" filter="url(#glow-filter)"/>
        <circle class="node nc" cx="350" cy="340" r="11" filter="url(#glow-filter)"/>
        <!-- Output nodes -->
        <circle class="node out" cx="490" cy="180" r="16" filter="url(#glow-filter)"/>
        <circle class="node out" cx="490" cy="300" r="16" filter="url(#glow-filter)"/>

        <!-- Signal paths (hidden, used for animateMotion) -->
        <path id="sig-a" d="M60,120 L200,80 L350,140 L490,180"  fill="none"/>
        <path id="sig-b" d="M60,240 L200,180 L350,240 L490,300" fill="none"/>
        <path id="sig-c" d="M60,360 L200,280 L350,340 L490,300" fill="none"/>
        <path id="sig-d" d="M60,120 L200,180 L350,240 L490,180" fill="none"/>

        <!-- Traveling signals -->
        <circle r="5" fill="#22D3EE" opacity="0.95" filter="url(#glow-filter)">
          <animateMotion dur="3.2s" repeatCount="indefinite" begin="0s"><mpath href="#sig-a"/></animateMotion>
        </circle>
        <circle r="5" fill="#A855F7" opacity="0.95" filter="url(#glow-filter)">
          <animateMotion dur="3.8s" repeatCount="indefinite" begin="1.1s"><mpath href="#sig-b"/></animateMotion>
        </circle>
        <circle r="4" fill="#34D399" opacity="0.9" filter="url(#glow-filter)">
          <animateMotion dur="2.9s" repeatCount="indefinite" begin="0.5s"><mpath href="#sig-c"/></animateMotion>
        </circle>
        <circle r="4" fill="#F472B6" opacity="0.9" filter="url(#glow-filter)">
          <animateMotion dur="4.1s" repeatCount="indefinite" begin="1.8s"><mpath href="#sig-d"/></animateMotion>
        </circle>
      </svg>

      <!-- ── Classroom holographic scene ── -->
      <svg class="classroom-svg" viewBox="0 0 500 220" preserveAspectRatio="xMidYMax meet">
        <defs>
          <linearGradient id="board-grad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#22D3EE" stop-opacity="0.15"/>
            <stop offset="100%" stop-color="#A855F7" stop-opacity="0.1"/>
          </linearGradient>
          <filter id="holo-glow">
            <feGaussianBlur stdDeviation="2.5" result="b"/>
            <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
        </defs>

        <!-- Holographic board -->
        <rect x="20" y="10" width="180" height="120" rx="6" fill="url(#board-grad)" stroke="#22D3EE" stroke-width="1.2" opacity="0.8"/>
        <!-- Board content (equations) - chalkboard handwriting style -->
        <text x="36" y="42" fill="#22D3EE" font-size="13.5" opacity="0.92" font-family="'Caveat', 'Segoe Print', cursive" font-weight="600">E = mc²</text>
        <text x="36" y="64" fill="#A855F7" font-size="12" opacity="0.88" font-family="'Caveat', 'Segoe Print', cursive" font-weight="600">∮ F·ds = Q/ε₀</text>
        <text x="36" y="84" fill="#22D3EE" font-size="12" opacity="0.85" font-family="'Caveat', 'Segoe Print', cursive" font-weight="600">∑ Fₙ = ma</text>
        <text x="36" y="104" fill="#34D399" font-size="12" opacity="0.85" font-family="'Caveat', 'Segoe Print', cursive" font-weight="600">∫₀ˣ f(t)dt</text>
        <!-- Board horizontal rule -->
        <line x1="20" y1="116" x2="200" y2="116" stroke="#22D3EE" stroke-width="0.7" opacity="0.5"/>
        <!-- Board scan line animation -->
        <rect x="20" y="10" width="180" height="4" fill="#22D3EE" opacity="0.06">
          <animate attributeName="y" from="10" to="130" dur="2.8s" repeatCount="indefinite"/>
          <animate attributeName="opacity" values="0.06;0.14;0.06" dur="2.8s" repeatCount="indefinite"/>
        </rect>

        <!-- ── Teacher figure ── -->
        <!-- Head -->
        <circle cx="238" cy="42" r="16" fill="rgba(139,92,246,0.45)" stroke="#A855F7" stroke-width="1.5" filter="url(#holo-glow)"/>
        <!-- Body -->
        <rect x="225" y="58" width="26" height="52" rx="5" fill="rgba(109,40,217,0.4)" stroke="#7C3AED" stroke-width="1.2"/>
        <!-- Arm pointing at board -->
        <line x1="225" y1="72" x2="198" y2="85" stroke="#A855F7" stroke-width="3.5" stroke-linecap="round"/>
        <!-- Pointer/laser beam -->
        <line x1="198" y1="85" x2="180" y2="80" stroke="#22D3EE" stroke-width="1.5" stroke-dasharray="6,3" opacity="0.9" filter="url(#holo-glow)"/>
        <circle cx="180" cy="80" r="3" fill="#22D3EE" filter="url(#holo-glow)" opacity="0.9"/>
        <!-- Other arm -->
        <line x1="251" y1="72" x2="264" y2="84" stroke="#A855F7" stroke-width="3.5" stroke-linecap="round"/>
        <!-- Legs -->
        <line x1="233" y1="110" x2="226" y2="145" stroke="#7C3AED" stroke-width="3.5" stroke-linecap="round"/>
        <line x1="245" y1="110" x2="252" y2="145" stroke="#7C3AED" stroke-width="3.5" stroke-linecap="round"/>

        <!-- ── Knowledge beams from teacher to students ── -->
        <path d="M250 75 Q310 30 330 110" stroke="#22D3EE" stroke-width="0.8" fill="none" opacity="0.25" stroke-dasharray="6,4"/>
        <path d="M250 75 Q360 20 395 110" stroke="#A855F7" stroke-width="0.8" fill="none" opacity="0.25" stroke-dasharray="6,4"/>
        <path d="M250 75 Q430 10 455 110" stroke="#34D399" stroke-width="0.8" fill="none" opacity="0.2"  stroke-dasharray="6,4"/>

        <!-- ── Student 1 ── -->
        <circle cx="330" cy="108" r="12" fill="rgba(34,211,238,0.35)" stroke="#22D3EE" stroke-width="1.3" filter="url(#holo-glow)"/>
        <rect x="320" y="120" width="20" height="28" rx="4" fill="rgba(8,145,178,0.3)" stroke="#0891B2" stroke-width="1"/>
        <rect x="308" y="148" width="44" height="5" rx="2.5" fill="rgba(34,211,238,0.2)" stroke="#0891B2" stroke-width="0.8"/>
        <!-- Notebook on desk -->
        <rect x="316" y="138" width="16" height="11" rx="1" fill="rgba(34,211,238,0.12)" stroke="#22D3EE" stroke-width="0.6"/>

        <!-- ── Student 2 ── -->
        <circle cx="395" cy="108" r="12" fill="rgba(168,85,247,0.35)" stroke="#A855F7" stroke-width="1.3" filter="url(#holo-glow)"/>
        <rect x="385" y="120" width="20" height="28" rx="4" fill="rgba(109,40,217,0.3)" stroke="#7C3AED" stroke-width="1"/>
        <rect x="373" y="148" width="44" height="5" rx="2.5" fill="rgba(168,85,247,0.2)" stroke="#7C3AED" stroke-width="0.8"/>
        <rect x="381" y="138" width="16" height="11" rx="1" fill="rgba(168,85,247,0.12)" stroke="#A855F7" stroke-width="0.6"/>

        <!-- ── Student 3 ── -->
        <circle cx="460" cy="108" r="12" fill="rgba(52,211,153,0.35)" stroke="#34D399" stroke-width="1.3" filter="url(#holo-glow)"/>
        <rect x="450" y="120" width="20" height="28" rx="4" fill="rgba(16,185,129,0.3)" stroke="#059669" stroke-width="1"/>
        <rect x="438" y="148" width="44" height="5" rx="2.5" fill="rgba(52,211,153,0.2)" stroke="#059669" stroke-width="0.8"/>
        <rect x="448" y="138" width="16" height="11" rx="1" fill="rgba(52,211,153,0.12)" stroke="#34D399" stroke-width="0.6"/>

        <!-- Ground line -->
        <line x1="20" y1="153" x2="490" y2="153" stroke="rgba(34,211,238,0.15)" stroke-width="1"/>

      </svg>

      <!-- ── Floating subject elements ── -->
      <div class="subjects">
        <!-- Math symbols as glowing text -->
        <span class="sym sym-math s1">π</span>
        <span class="sym sym-math s2">∑</span>
        <span class="sym sym-math s3">∞</span>
        <span class="sym sym-purple s4">∫</span>
        <span class="sym sym-green s5">√2</span>
        <span class="sym sym-purple s6">Δ</span>
        <span class="sym sym-math s7">E=mc²</span>

        <!-- 生物 Microscope — right side upper -->
        <div class="icon-chip ic1">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#22D3EE" stroke-width="1.5" stroke-linecap="round">
            <path d="M6 18h12M10 6l2-3 2 3M10 6v8h4V6M12 18v-4"/>
            <circle cx="12" cy="4" r="1.5"/>
            <path d="M9 14H7a2 2 0 0 0-2 2v1h14v-1a2 2 0 0 0-2-2h-2"/>
          </svg>
          <span>生物</span>
        </div>

        <!-- 数学 Triangle ruler — moved to bottom-left open area -->
        <div class="icon-chip ic2">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#A855F7" stroke-width="1.5" stroke-linecap="round">
            <polygon points="4,20 20,20 4,4"/>
            <line x1="4" y1="14" x2="14" y2="14"/>
            <line x1="4" y1="8" x2="8" y2="8"/>
          </svg>
          <span>数学</span>
        </div>

        <!-- 化学 Flask -->
        <div class="icon-chip ic3">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#34D399" stroke-width="1.5" stroke-linecap="round">
            <path d="M9 3h6M9 3v6l-5 9a1 1 0 0 0 .9 1.5h14.2a1 1 0 0 0 .9-1.5L15 9V3"/>
            <line x1="6.5" y1="14" x2="17.5" y2="14"/>
          </svg>
          <span>化学</span>
        </div>

        <!-- 物理 Atom -->
        <div class="icon-chip ic4">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#F472B6" stroke-width="1.5" stroke-linecap="round">
            <circle cx="12" cy="12" r="2"/>
            <ellipse cx="12" cy="12" rx="10" ry="4"/>
            <ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(60 12 12)"/>
            <ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(120 12 12)"/>
          </svg>
          <span>物理</span>
        </div>

        <!-- 英语 Letter A -->
        <div class="icon-chip ic5">
          <span class="chip-letter">A</span>
          <span>英语</span>
        </div>

        <!-- 地理 Globe -->
        <div class="icon-chip ic6">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#60A5FA" stroke-width="1.5" stroke-linecap="round">
            <circle cx="12" cy="12" r="9"/>
            <path d="M12 3a14.5 14.5 0 0 0 0 18M12 3a14.5 14.5 0 0 1 0 18"/>
            <line x1="3" y1="12" x2="21" y2="12"/>
          </svg>
          <span>地理</span>
        </div>

        <!-- 语文 Book -->
        <div class="icon-chip ic7">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#A855F7" stroke-width="1.5" stroke-linecap="round">
            <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
            <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
          </svg>
          <span>语文</span>
        </div>

        <!-- 政治 Balance scale (replaces DNA) -->
        <div class="icon-chip ic8">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#34D399" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="3" x2="12" y2="21"/>
            <path d="M5 21h14"/>
            <path d="M5 8l-2 5h4L5 8z"/>
            <path d="M19 8l-2 5h4L19 8z"/>
            <line x1="5" y1="8" x2="19" y2="8"/>
          </svg>
          <span>政治</span>
        </div>

        <!-- 历史 Hourglass (new) -->
        <div class="icon-chip ic9">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#F97316" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M5 22h14"/>
            <path d="M5 2h14"/>
            <path d="M17 22v-4.172a2 2 0 0 0-.586-1.414L12 12l-4.414 4.414A2 2 0 0 0 7 17.828V22"/>
            <path d="M7 2v4.172a2 2 0 0 0 .586 1.414L12 12l4.414-4.414A2 2 0 0 0 17 6.172V2"/>
          </svg>
          <span>历史</span>
        </div>
      </div>

      <!-- ── Brand + Headline ── -->
      <div class="left-content">
        <div class="brand">
          <div class="brand-logo">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M12 3L2 8l10 5 10-5-10-5z" fill="white" opacity="0.95"/>
              <path d="M2 16l10 5 10-5" stroke="white" stroke-width="2" stroke-linecap="round"/>
              <path d="M2 12l10 5 10-5" stroke="white" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </div>
          <span class="brand-name">TeachSim</span>
        </div>

        <h1 class="headline">
          <span class="hl-line">让 AI 成为</span>
          <span class="hl-line hl-neon">每位老师</span>
          <span class="hl-line">最好的陪练</span>
        </h1>
        <p class="tagline">上传教案，模拟真实课堂<br>获取定制化教学反馈报告</p>
      </div>
    </div>

    <!-- ═══════════════════ RIGHT PANEL ═══════════════════ -->
    <div class="right-panel">
      <div class="glass-card">
        <!-- Glowing border ring -->
        <div class="card-glow-ring"></div>

        <!-- Tab bar -->
        <div class="tab-bar">
          <button :class="['tab-btn', { active: mode === 'login' }]" @click="switchMode('login')">登录</button>
          <button :class="['tab-btn', { active: mode === 'register' }]" @click="switchMode('register')">注册</button>
        </div>

        <!-- Login form -->
        <form v-if="mode === 'login'" @submit.prevent="doLogin" class="form" key="login">
          <div class="form-group">
            <label>用户名</label>
            <input v-model="loginForm.username" type="text" placeholder="请输入用户名" autocomplete="username" required />
          </div>
          <div class="form-group">
            <label>密码</label>
            <div class="input-wrap">
              <input v-model="loginForm.password" :type="showPwd ? 'text' : 'password'" placeholder="请输入密码" autocomplete="current-password" required />
              <button type="button" class="eye-btn" @click="showPwd = !showPwd" tabindex="-1">
                <EyeIcon :open="showPwd"/>
              </button>
            </div>
          </div>
          <p v-if="successMsg" class="msg-ok">✓ {{ successMsg }}</p>
          <p v-else-if="errorMsg" class="msg-err">{{ errorMsg }}</p>
          <button type="submit" class="submit-btn" :disabled="submitting">
            <span v-if="submitting" class="btn-spinner"></span>
            {{ submitting ? '验证中…' : '登录' }}
          </button>
          <p class="form-footer">还没有账号？<button type="button" class="link-btn" @click="switchMode('register')">立即注册</button></p>
        </form>

        <!-- Register form -->
        <form v-else @submit.prevent="doRegister" class="form" key="register">
          <div class="form-group">
            <label>用户名</label>
            <input v-model="regForm.username" type="text" placeholder="建议英文或拼音" autocomplete="username" required />
          </div>
          <div class="form-group">
            <label>密码</label>
            <div class="input-wrap">
              <input v-model="regForm.password" :type="showPwd ? 'text' : 'password'" placeholder="至少 6 位" autocomplete="new-password" required minlength="6" />
              <button type="button" class="eye-btn" @click="showPwd = !showPwd" tabindex="-1">
                <EyeIcon :open="showPwd"/>
              </button>
            </div>
          </div>
          <div class="form-group">
            <label>确认密码</label>
            <div class="input-wrap">
              <input v-model="regForm.confirm" :type="showPwd2 ? 'text' : 'password'" placeholder="再次输入密码" autocomplete="new-password" required />
              <button type="button" class="eye-btn" @click="showPwd2 = !showPwd2" tabindex="-1">
                <EyeIcon :open="showPwd2"/>
              </button>
            </div>
            <p v-if="regForm.confirm && regForm.password !== regForm.confirm" class="field-warn">两次密码不一致</p>
          </div>
          <p v-if="errorMsg" class="msg-err">{{ errorMsg }}</p>
          <button type="submit" class="submit-btn" :disabled="submitting || (!!regForm.confirm && regForm.password !== regForm.confirm)">
            <span v-if="submitting" class="btn-spinner"></span>
            {{ submitting ? '创建中…' : '创建账号' }}
          </button>
          <p class="form-footer">已有账号？<button type="button" class="link-btn" @click="switchMode('login')">直接登录</button></p>
        </form>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/authStore.js'

const EyeIcon = {
  props: ['open'],
  template: `
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <template v-if="!open">
        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
        <circle cx="12" cy="12" r="3"/>
      </template>
      <template v-else>
        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
        <line x1="1" y1="1" x2="23" y2="23"/>
      </template>
    </svg>`
}

const router = useRouter()
const auth = useAuthStore()

const mode = ref('login')
const showPwd = ref(false)
const showPwd2 = ref(false)
const errorMsg = ref('')
const successMsg = ref('')
const submitting = ref(false)

const loginForm = ref({ username: '', password: '' })
const regForm = ref({ username: '', password: '', confirm: '' })

function switchMode(m) {
  mode.value = m
  errorMsg.value = ''
  successMsg.value = ''
  showPwd.value = false
  showPwd2.value = false
}

async function doLogin() {
  errorMsg.value = ''
  submitting.value = true
  await new Promise(r => setTimeout(r, 400))
  const res = auth.login(loginForm.value.username, loginForm.value.password)
  submitting.value = false
  if (res.ok) {
    router.push('/setup')
  } else {
    errorMsg.value = res.msg
  }
}

async function doRegister() {
  errorMsg.value = ''
  if (regForm.value.password !== regForm.value.confirm) {
    errorMsg.value = '两次密码输入不一致'
    return
  }
  if (regForm.value.password.length < 6) {
    errorMsg.value = '密码至少需要 6 位'
    return
  }
  submitting.value = true
  await new Promise(r => setTimeout(r, 400))
  const res = auth.register(regForm.value.username, regForm.value.username, regForm.value.password, '实习教师')
  submitting.value = false
  if (res.ok) {
    loginForm.value.username = regForm.value.username
    loginForm.value.password = ''
    regForm.value = { username: '', password: '', confirm: '' }
    switchMode('login')
    successMsg.value = '注册成功，请登录'
    setTimeout(() => successMsg.value = '', 4000)
  } else {
    errorMsg.value = res.msg
  }
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Caveat:wght@400;600;700&display=swap');
/* ═══════════════════════════════════════════
   BASE
═══════════════════════════════════════════ */
.login-page {
  display: flex;
  min-height: 100vh;
  width: 100vw;
  box-sizing: border-box;
  padding-right: 72px; /* 右侧预留“三格”空白 */
  overflow: hidden;
  position: relative;
  background: #020817;
}

/* ═══════════════════════════════════════════
   GLOBAL BACKGROUND
═══════════════════════════════════════════ */
.global-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
  /* Deep space gradient */
  background: radial-gradient(ellipse at 20% 30%, #0D1B4B 0%, transparent 55%),
              radial-gradient(ellipse at 80% 70%, #2D1265 0%, transparent 55%),
              linear-gradient(160deg, #020817 0%, #080C1E 40%, #0A0520 70%, #020817 100%);
}

.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(34,211,238,0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(34,211,238,0.04) 1px, transparent 1px);
  background-size: 52px 52px;
}

.glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  pointer-events: none;
}
.g1 { width: 500px; height: 500px; background: rgba(29,78,216,0.3);  top: -120px; left: -100px; animation: gp 7s ease-in-out infinite; }
.g2 { width: 420px; height: 420px; background: rgba(109,40,217,0.25); bottom: -80px; right: -60px; animation: gp 9s ease-in-out infinite reverse; }
.g3 { width: 300px; height: 300px; background: rgba(6,182,212,0.18);  top: 40%;   left: 35%;   animation: gp 11s ease-in-out infinite 2s; }
.g4 { width: 200px; height: 200px; background: rgba(167,139,250,0.15); top: 10%;  right: 30%;  animation: gp 8s ease-in-out infinite 1s; }

@keyframes gp {
  0%,100% { opacity: 0.6; transform: scale(1); }
  50%      { opacity: 1;   transform: scale(1.15); }
}

.scan-lines {
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    to bottom,
    transparent 0px,
    transparent 3px,
    rgba(0,0,0,0.06) 3px,
    rgba(0,0,0,0.06) 4px
  );
  pointer-events: none;
}

/* ═══════════════════════════════════════════
   LEFT PANEL
═══════════════════════════════════════════ */
.left-panel {
  flex: 1;
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  min-width: 0;
}

/* Neural net - full background */
.neural-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0.45;
  z-index: 1;
}

.edge {
  stroke: rgba(34,211,238,0.18);
  stroke-width: 1;
}

.node {
  fill: rgba(30,58,138,0.7);
  stroke: rgba(147,197,253,0.6);
  stroke-width: 1.5;
  animation: np 3.5s ease-in-out infinite;
}
.node.nc { fill: rgba(14,116,144,0.6); stroke: rgba(34,211,238,0.8); }
.node.np { fill: rgba(109,40,217,0.6); stroke: rgba(167,139,250,0.8); }
.node.out{
  fill: rgba(5,150,105,0.65);
  stroke: rgba(52,211,153,0.9);
  animation: np 2.5s ease-in-out infinite;
}
@keyframes np {
  0%,100% { opacity: 0.65; }
  50%      { opacity: 1; }
}

/* Classroom scene — anchored to bottom, only covers lower 30% */
.classroom-svg {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  width: 100%;
  height: 30%;
  z-index: 2;
  opacity: 0.55;
}

/* Floating subject icons */
.subjects {
  position: absolute;
  inset: 0;
  z-index: 3;
  pointer-events: none;
}

/* Glowing math symbols */
.sym {
  position: absolute;
  font-family: 'Georgia', serif;
  font-style: italic;
  animation: sym-float 9s ease-in-out infinite;
}
.sym-math   { color: rgba(34,211,238,0.5);  text-shadow: 0 0 12px rgba(34,211,238,0.6); }
.sym-purple { color: rgba(168,85,247,0.5);  text-shadow: 0 0 12px rgba(168,85,247,0.6); }
.sym-green  { color: rgba(52,211,153,0.45); text-shadow: 0 0 12px rgba(52,211,153,0.6); }

.s1 { font-size: 28px; top: 12%; left: 5%;  animation-delay: 0s; }
.s2 { font-size: 22px; top: 30%; left: 82%; animation-delay: 1.5s; }
.s3 { font-size: 26px; top: 60%; left: 4%;  animation-delay: 3s; }
.s4 { font-size: 30px; top: 20%; left: 70%; animation-delay: 0.8s; }
.s5 { font-size: 18px; top: 72%; left: 78%; animation-delay: 2.2s; }
.s6 { font-size: 24px; top: 8%;  left: 50%; animation-delay: 4s; }
.s7 { font-size: 14px; top: 82%; left: 55%; animation-delay: 1.8s; font-family: monospace; font-style: normal; letter-spacing: 1px; }

@keyframes sym-float {
  0%,100% { transform: translateY(0)    rotate(-4deg); opacity: 0.5; }
  33%      { transform: translateY(-16px) rotate(3deg);  opacity: 0.8; }
  66%      { transform: translateY(-6px)  rotate(-2deg); opacity: 0.6; }
}

/* Subject icon chips */
.icon-chip {
  position: absolute;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  background: rgba(2,8,23,0.6);
  border-radius: 20px;
  animation: chip-float 10s ease-in-out infinite;
  backdrop-filter: blur(6px);
}
.icon-chip span { font-size: 11px; font-weight: 600; color: rgba(255,255,255,0.55); }
.chip-letter {
  font-size: 17px !important;
  font-weight: 900 !important;
  font-style: italic;
  color: #FBBF24 !important;
  text-shadow: 0 0 10px rgba(251,191,36,0.7);
  line-height: 1;
  font-family: 'Georgia', serif;
}

/* All chips: avoid top-left quadrant (0-45% top, 0-60% left) where headline lives */
.ic1 { top: 5%;  left: 64%; border: 1px solid rgba(34,211,238,0.3);  box-shadow: 0 0 12px rgba(34,211,238,0.15);  animation-delay: 0s;   animation-duration: 9s; }
.ic2 { top: 72%; left: 4%;  border: 1px solid rgba(168,85,247,0.3);  box-shadow: 0 0 12px rgba(168,85,247,0.15);  animation-delay: 1.2s; animation-duration: 11s; }
.ic3 { top: 26%; left: 74%; border: 1px solid rgba(52,211,153,0.3);  box-shadow: 0 0 12px rgba(52,211,153,0.15);  animation-delay: 2.5s; animation-duration: 8s; }
.ic4 { top: 48%; left: 5%;  border: 1px solid rgba(244,114,182,0.3); box-shadow: 0 0 12px rgba(244,114,182,0.15); animation-delay: 0.7s; animation-duration: 12s; }
.ic5 { top: 3%;  left: 35%; border: 1px solid rgba(251,191,36,0.3);  box-shadow: 0 0 12px rgba(251,191,36,0.15);  animation-delay: 3.5s; animation-duration: 10s; }
.ic6 { top: 55%; left: 80%; border: 1px solid rgba(96,165,250,0.3);  box-shadow: 0 0 12px rgba(96,165,250,0.15);  animation-delay: 1.8s; animation-duration: 9s; }
.ic7 { top: 36%; left: 62%; border: 1px solid rgba(168,85,247,0.3);  box-shadow: 0 0 12px rgba(168,85,247,0.15);  animation-delay: 4.2s; animation-duration: 11s; }
.ic8 { top: 15%; left: 76%; border: 1px solid rgba(52,211,153,0.3);  box-shadow: 0 0 12px rgba(52,211,153,0.15);  animation-delay: 2s;   animation-duration: 8.5s; }
.ic9 { top: 68%; left: 56%; border: 1px solid rgba(249,115,22,0.3);  box-shadow: 0 0 12px rgba(249,115,22,0.15);  animation-delay: 1.5s; animation-duration: 10s; }

@keyframes chip-float {
  0%,100% { transform: translateY(0px); }
  50%      { transform: translateY(-12px); }
}

/* Left content text */
.left-content {
  position: relative;
  z-index: 4;
  padding: 0 56px;
  max-width: 560px;
  width: 100%;
  /* push content slightly above center to give room for classroom scene below */
  margin-bottom: 120px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 36px;
}

.brand-logo {
  width: 64px;
  height: 64px;
  background: rgba(37,99,235,0.35);
  border: 1px solid rgba(34,211,238,0.4);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 22px rgba(34,211,238,0.25);
  backdrop-filter: blur(8px);
}

.brand-name {
  font-size: 32px;
  font-weight: 800;
  color: rgba(255,255,255,0.95);
  letter-spacing: -0.5px;
  text-shadow: 0 0 24px rgba(34,211,238,0.4);
}

.headline {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: 22px;
}
.hl-line {
  display: block;
  font-size: 72px;
  font-weight: 900;
  line-height: 1.15;
  letter-spacing: -3px;
  color: rgba(255,255,255,0.95);
  text-shadow: 0 2px 20px rgba(0,0,0,0.6), 0 0 40px rgba(255,255,255,0.06);
}
.hl-neon {
  background: linear-gradient(90deg, #22D3EE, #A855F7, #22D3EE);
  background-size: 200% auto;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  animation: text-shine 4s linear infinite;
  text-shadow: none;
}
@keyframes text-shine {
  to { background-position: 200% center; }
}

.tagline {
  font-size: 15px;
  color: rgba(255,255,255,0.72);
  line-height: 1.85;
  text-shadow: 0 1px 16px rgba(0,0,0,0.8), 0 0 30px rgba(34,211,238,0.15);
  font-weight: 400;
  letter-spacing: 0.4px;
}

/* ═══════════════════════════════════════════
   RIGHT PANEL — Glassmorphism
═══════════════════════════════════════════ */
.right-panel {
  width: 420px;
  min-width: 420px;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  position: relative;
  z-index: 5;
  padding: 40px 0 40px 0;
  margin-left: -180px; /* 维持卡片与左侧图案的相对距离 */
}

.glass-card {
  width: 100%;
  position: relative;
  background: rgba(5, 12, 35, 0.72);
  backdrop-filter: blur(28px) saturate(180%);
  border-radius: 22px;
  border: 1px solid rgba(34,211,238,0.22);
  box-shadow:
    0 0 0 1px rgba(168,85,247,0.12),
    0 24px 64px rgba(0,0,0,0.65),
    0 0 40px rgba(34,211,238,0.06),
    inset 0 1px 0 rgba(255,255,255,0.06);
  padding: 36px 34px 30px;
  overflow: hidden;
}

/* Glowing top border accent */
.card-glow-ring {
  position: absolute;
  top: 0; left: 10%; right: 10%;
  height: 1px;
  background: linear-gradient(90deg, transparent, #22D3EE, #A855F7, transparent);
  opacity: 0.7;
}

/* Tab bar */
.tab-bar {
  display: flex;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 3px;
  margin-bottom: 28px;
}

.tab-btn {
  flex: 1;
  padding: 9px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  color: rgba(255,255,255,0.4);
  cursor: pointer;
  transition: all 0.25s;
}

.tab-btn.active {
  background: rgba(34,211,238,0.12);
  color: #22D3EE;
  box-shadow: 0 0 16px rgba(34,211,238,0.2), inset 0 0 12px rgba(34,211,238,0.05);
  border: 1px solid rgba(34,211,238,0.25);
}

/* Form */
.form { display: flex; flex-direction: column; gap: 18px; }

.form-group { display: flex; flex-direction: column; gap: 6px; }

.form-group label {
  font-size: 12.5px;
  font-weight: 600;
  color: rgba(255,255,255,0.5);
  letter-spacing: 0.4px;
  text-transform: uppercase;
}

.form-group input {
  height: 44px;
  background: rgba(255,255,255,0.05);
  border: 1.5px solid rgba(255,255,255,0.1);
  border-radius: 10px;
  padding: 0 14px;
  font-size: 14px;
  color: rgba(255,255,255,0.88);
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
  width: 100%;
}

.form-group input::placeholder { color: rgba(255,255,255,0.25); }

.form-group input:focus {
  border-color: #22D3EE;
  background: rgba(34,211,238,0.06);
  box-shadow: 0 0 0 3px rgba(34,211,238,0.12), 0 0 16px rgba(34,211,238,0.08);
}

.input-wrap { position: relative; }
.input-wrap input { padding-right: 44px; }

.eye-btn {
  position: absolute;
  right: 13px;
  top: 50%;
  transform: translateY(-50%);
  color: rgba(255,255,255,0.3);
  cursor: pointer;
  display: flex;
  align-items: center;
  transition: color 0.15s;
}
.eye-btn:hover { color: #22D3EE; }

.field-warn {
  font-size: 12px;
  color: #FBBF24;
  margin-top: 3px;
}

.msg-err {
  font-size: 12.5px;
  color: #FCA5A5;
  background: rgba(239,68,68,0.12);
  border: 1px solid rgba(239,68,68,0.25);
  border-radius: 8px;
  padding: 9px 13px;
  margin: -4px 0;
}

.msg-ok {
  font-size: 12.5px;
  color: #6EE7B7;
  background: rgba(52,211,153,0.1);
  border: 1px solid rgba(52,211,153,0.25);
  border-radius: 8px;
  padding: 9px 13px;
  margin: -4px 0;
}

.submit-btn {
  height: 48px;
  background: linear-gradient(135deg, #1D4ED8 0%, #7C3AED 100%);
  color: white;
  border-radius: 11px;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.25s;
  margin-top: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  letter-spacing: 0.3px;
  position: relative;
  overflow: hidden;
}

.submit-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(34,211,238,0.15), rgba(168,85,247,0.15));
  opacity: 0;
  transition: opacity 0.25s;
}

.submit-btn:hover:not(:disabled)::before { opacity: 1; }

.submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(124,58,237,0.5), 0 0 0 1px rgba(34,211,238,0.3);
}

.submit-btn:disabled { opacity: 0.45; cursor: not-allowed; }

.btn-spinner {
  width: 16px; height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.form-footer {
  text-align: center;
  font-size: 13px;
  color: rgba(255,255,255,0.3);
  margin-top: -4px;
}

.link-btn {
  color: #22D3EE;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  text-shadow: 0 0 10px rgba(34,211,238,0.4);
}
.link-btn:hover {
  color: #67E8F9;
  text-shadow: 0 0 15px rgba(34,211,238,0.7);
}
</style>
