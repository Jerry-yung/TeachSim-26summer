<template>
  <div class="login-page">
    <div class="global-bg">
      <div class="bg-grid"></div>
      <div class="glow g1"></div>
      <div class="glow g2"></div>
      <div class="glow g3"></div>
      <div class="glow g4"></div>
      <div class="scan-lines"></div>
    </div>

    <section class="left-panel" aria-hidden="true">
      <svg class="neural-svg" viewBox="0 0 600 500" preserveAspectRatio="xMidYMid slice">
        <defs>
          <filter id="login-glow-filter">
            <feGaussianBlur stdDeviation="3" result="blur"/>
            <feMerge>
              <feMergeNode in="blur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>

        <line class="edge" x1="60" y1="120" x2="200" y2="80"/>
        <line class="edge" x1="60" y1="120" x2="200" y2="180"/>
        <line class="edge" x1="60" y1="240" x2="200" y2="80"/>
        <line class="edge" x1="60" y1="240" x2="200" y2="180"/>
        <line class="edge" x1="60" y1="240" x2="200" y2="280"/>
        <line class="edge" x1="60" y1="360" x2="200" y2="180"/>
        <line class="edge" x1="60" y1="360" x2="200" y2="280"/>
        <line class="edge" x1="200" y1="80" x2="350" y2="140"/>
        <line class="edge" x1="200" y1="80" x2="350" y2="240"/>
        <line class="edge" x1="200" y1="180" x2="350" y2="140"/>
        <line class="edge" x1="200" y1="180" x2="350" y2="240"/>
        <line class="edge" x1="200" y1="180" x2="350" y2="340"/>
        <line class="edge" x1="200" y1="280" x2="350" y2="240"/>
        <line class="edge" x1="200" y1="280" x2="350" y2="340"/>
        <line class="edge" x1="350" y1="140" x2="490" y2="180"/>
        <line class="edge" x1="350" y1="240" x2="490" y2="180"/>
        <line class="edge" x1="350" y1="240" x2="490" y2="300"/>
        <line class="edge" x1="350" y1="340" x2="490" y2="300"/>

        <circle class="node node-cyan" cx="60" cy="120" r="9" filter="url(#login-glow-filter)"/>
        <circle class="node node-purple" cx="60" cy="240" r="9" filter="url(#login-glow-filter)"/>
        <circle class="node node-cyan" cx="60" cy="360" r="9" filter="url(#login-glow-filter)"/>
        <circle class="node node-purple" cx="200" cy="80" r="11" filter="url(#login-glow-filter)"/>
        <circle class="node node-cyan" cx="200" cy="180" r="13" filter="url(#login-glow-filter)"/>
        <circle class="node node-purple" cx="200" cy="280" r="11" filter="url(#login-glow-filter)"/>
        <circle class="node node-cyan" cx="350" cy="140" r="11" filter="url(#login-glow-filter)"/>
        <circle class="node node-purple" cx="350" cy="240" r="13" filter="url(#login-glow-filter)"/>
        <circle class="node node-cyan" cx="350" cy="340" r="11" filter="url(#login-glow-filter)"/>
        <circle class="node node-output" cx="490" cy="180" r="16" filter="url(#login-glow-filter)"/>
        <circle class="node node-output" cx="490" cy="300" r="16" filter="url(#login-glow-filter)"/>

        <path id="login-sig-a" d="M60,120 L200,80 L350,140 L490,180" fill="none"/>
        <path id="login-sig-b" d="M60,240 L200,180 L350,240 L490,300" fill="none"/>
        <path id="login-sig-c" d="M60,360 L200,280 L350,340 L490,300" fill="none"/>
        <path id="login-sig-d" d="M60,120 L200,180 L350,240 L490,180" fill="none"/>

        <circle r="5" fill="#22D3EE" opacity="0.95" filter="url(#login-glow-filter)">
          <animateMotion dur="3.2s" repeatCount="indefinite" begin="0s">
            <mpath href="#login-sig-a"/>
          </animateMotion>
        </circle>
        <circle r="5" fill="#A855F7" opacity="0.95" filter="url(#login-glow-filter)">
          <animateMotion dur="3.8s" repeatCount="indefinite" begin="1.1s">
            <mpath href="#login-sig-b"/>
          </animateMotion>
        </circle>
        <circle r="4" fill="#34D399" opacity="0.9" filter="url(#login-glow-filter)">
          <animateMotion dur="2.9s" repeatCount="indefinite" begin="0.5s">
            <mpath href="#login-sig-c"/>
          </animateMotion>
        </circle>
        <circle r="4" fill="#F472B6" opacity="0.9" filter="url(#login-glow-filter)">
          <animateMotion dur="4.1s" repeatCount="indefinite" begin="1.8s">
            <mpath href="#login-sig-d"/>
          </animateMotion>
        </circle>
      </svg>

      <svg class="classroom-svg" viewBox="0 0 500 220" preserveAspectRatio="xMidYMax meet">
        <defs>
          <linearGradient id="login-board-grad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#22D3EE" stop-opacity="0.15"/>
            <stop offset="100%" stop-color="#A855F7" stop-opacity="0.1"/>
          </linearGradient>
          <filter id="login-holo-glow">
            <feGaussianBlur stdDeviation="2.5" result="b"/>
            <feMerge>
              <feMergeNode in="b"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>

        <rect x="20" y="10" width="180" height="120" rx="6" fill="url(#login-board-grad)" stroke="#22D3EE" stroke-width="1.2" opacity="0.8"/>
        <text x="36" y="42" fill="#22D3EE" font-size="13.5" opacity="0.92" font-family="'Caveat', 'Segoe Print', cursive" font-weight="600">E = mc²</text>
        <text x="36" y="64" fill="#A855F7" font-size="12" opacity="0.88" font-family="'Caveat', 'Segoe Print', cursive" font-weight="600">∮ F·ds = Q/ε₀</text>
        <text x="36" y="84" fill="#22D3EE" font-size="12" opacity="0.85" font-family="'Caveat', 'Segoe Print', cursive" font-weight="600">∑ Fₙ = ma</text>
        <text x="36" y="104" fill="#34D399" font-size="12" opacity="0.85" font-family="'Caveat', 'Segoe Print', cursive" font-weight="600">∫₀ˣ f(t)dt</text>
        <line x1="20" y1="116" x2="200" y2="116" stroke="#22D3EE" stroke-width="0.7" opacity="0.5"/>
        <rect x="20" y="10" width="180" height="4" fill="#22D3EE" opacity="0.06">
          <animate attributeName="y" from="10" to="130" dur="2.8s" repeatCount="indefinite"/>
          <animate attributeName="opacity" values="0.06;0.14;0.06" dur="2.8s" repeatCount="indefinite"/>
        </rect>

        <circle cx="238" cy="42" r="16" fill="rgba(139,92,246,0.45)" stroke="#A855F7" stroke-width="1.5" filter="url(#login-holo-glow)"/>
        <rect x="225" y="58" width="26" height="52" rx="5" fill="rgba(109,40,217,0.4)" stroke="#7C3AED" stroke-width="1.2"/>
        <line x1="225" y1="72" x2="198" y2="85" stroke="#A855F7" stroke-width="3.5" stroke-linecap="round"/>
        <line x1="198" y1="85" x2="180" y2="80" stroke="#22D3EE" stroke-width="1.5" stroke-dasharray="6,3" opacity="0.9" filter="url(#login-holo-glow)"/>
        <circle cx="180" cy="80" r="3" fill="#22D3EE" filter="url(#login-holo-glow)" opacity="0.9"/>
        <line x1="251" y1="72" x2="264" y2="84" stroke="#A855F7" stroke-width="3.5" stroke-linecap="round"/>
        <line x1="233" y1="110" x2="226" y2="145" stroke="#7C3AED" stroke-width="3.5" stroke-linecap="round"/>
        <line x1="245" y1="110" x2="252" y2="145" stroke="#7C3AED" stroke-width="3.5" stroke-linecap="round"/>

        <path d="M250 75 Q310 30 330 110" stroke="#22D3EE" stroke-width="0.8" fill="none" opacity="0.25" stroke-dasharray="6,4"/>
        <path d="M250 75 Q360 20 395 110" stroke="#A855F7" stroke-width="0.8" fill="none" opacity="0.25" stroke-dasharray="6,4"/>
        <path d="M250 75 Q430 10 455 110" stroke="#34D399" stroke-width="0.8" fill="none" opacity="0.2" stroke-dasharray="6,4"/>

        <circle cx="330" cy="108" r="12" fill="rgba(34,211,238,0.35)" stroke="#22D3EE" stroke-width="1.3" filter="url(#login-holo-glow)"/>
        <rect x="320" y="120" width="20" height="28" rx="4" fill="rgba(8,145,178,0.3)" stroke="#0891B2" stroke-width="1"/>
        <rect x="308" y="148" width="44" height="5" rx="2.5" fill="rgba(34,211,238,0.2)" stroke="#0891B2" stroke-width="0.8"/>
        <rect x="316" y="138" width="16" height="11" rx="1" fill="rgba(34,211,238,0.12)" stroke="#22D3EE" stroke-width="0.6"/>

        <circle cx="395" cy="108" r="12" fill="rgba(168,85,247,0.35)" stroke="#A855F7" stroke-width="1.3" filter="url(#login-holo-glow)"/>
        <rect x="385" y="120" width="20" height="28" rx="4" fill="rgba(109,40,217,0.3)" stroke="#7C3AED" stroke-width="1"/>
        <rect x="373" y="148" width="44" height="5" rx="2.5" fill="rgba(168,85,247,0.2)" stroke="#7C3AED" stroke-width="0.8"/>
        <rect x="381" y="138" width="16" height="11" rx="1" fill="rgba(168,85,247,0.12)" stroke="#A855F7" stroke-width="0.6"/>

        <circle cx="460" cy="108" r="12" fill="rgba(52,211,153,0.35)" stroke="#34D399" stroke-width="1.3" filter="url(#login-holo-glow)"/>
        <rect x="450" y="120" width="20" height="28" rx="4" fill="rgba(16,185,129,0.3)" stroke="#059669" stroke-width="1"/>
        <rect x="438" y="148" width="44" height="5" rx="2.5" fill="rgba(52,211,153,0.2)" stroke="#059669" stroke-width="0.8"/>
        <rect x="448" y="138" width="16" height="11" rx="1" fill="rgba(52,211,153,0.12)" stroke="#34D399" stroke-width="0.6"/>

        <line x1="20" y1="153" x2="490" y2="153" stroke="rgba(34,211,238,0.15)" stroke-width="1"/>
      </svg>

      <div class="subjects">
        <span class="sym sym-cyan s1">π</span>
        <span class="sym sym-cyan s2">∑</span>
        <span class="sym sym-cyan s3">∞</span>
        <span class="sym sym-purple s4">∫</span>
        <span class="sym sym-green s5">√2</span>
        <span class="sym sym-purple s6">Δ</span>
        <span class="sym sym-cyan s7">E=mc²</span>

        <div class="icon-chip ic1">
          <span class="chip-letter">A</span>
          <span>英语</span>
        </div>
        <div class="icon-chip ic2">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#22D3EE" stroke-width="1.5" stroke-linecap="round">
            <path d="M6 18h12M10 6l2-3 2 3M10 6v8h4V6M12 18v-4"/>
            <circle cx="12" cy="4" r="1.5"/>
            <path d="M9 14H7a2 2 0 0 0-2 2v1h14v-1a2 2 0 0 0-2-2h-2"/>
          </svg>
          <span>生物</span>
        </div>
        <div class="icon-chip ic3">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#34D399" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="3" x2="12" y2="21"/>
            <path d="M5 21h14"/>
            <path d="M5 8l-2 5h4L5 8z"/>
            <path d="M19 8l-2 5h4L19 8z"/>
            <line x1="5" y1="8" x2="19" y2="8"/>
          </svg>
          <span>政治</span>
        </div>
        <div class="icon-chip ic4">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#34D399" stroke-width="1.5" stroke-linecap="round">
            <path d="M9 3h6M9 3v6l-5 9a1 1 0 0 0 .9 1.5h14.2a1 1 0 0 0 .9-1.5L15 9V3"/>
            <line x1="6.5" y1="14" x2="17.5" y2="14"/>
          </svg>
          <span>化学</span>
        </div>
        <div class="icon-chip ic5">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#A855F7" stroke-width="1.5" stroke-linecap="round">
            <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
            <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
          </svg>
          <span>语文</span>
        </div>
        <div class="icon-chip ic6">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#60A5FA" stroke-width="1.5" stroke-linecap="round">
            <circle cx="12" cy="12" r="9"/>
            <path d="M12 3a14.5 14.5 0 0 0 0 18M12 3a14.5 14.5 0 0 1 0 18"/>
            <line x1="3" y1="12" x2="21" y2="12"/>
          </svg>
          <span>地理</span>
        </div>
        <div class="icon-chip ic7">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#F97316" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M5 22h14"/>
            <path d="M5 2h14"/>
            <path d="M17 22v-4.172a2 2 0 0 0-.586-1.414L12 12l-4.414 4.414A2 2 0 0 0 7 17.828V22"/>
            <path d="M7 2v4.172a2 2 0 0 0 .586 1.414L12 12l4.414-4.414A2 2 0 0 0 17 6.172V2"/>
          </svg>
          <span>历史</span>
        </div>
        <div class="icon-chip ic8">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#F472B6" stroke-width="1.5" stroke-linecap="round">
            <circle cx="12" cy="12" r="2"/>
            <ellipse cx="12" cy="12" rx="10" ry="4"/>
            <ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(60 12 12)"/>
            <ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(120 12 12)"/>
          </svg>
          <span>物理</span>
        </div>
        <div class="icon-chip ic9">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#A855F7" stroke-width="1.5" stroke-linecap="round">
            <polygon points="4,20 20,20 4,4"/>
            <line x1="4" y1="14" x2="14" y2="14"/>
            <line x1="4" y1="8" x2="8" y2="8"/>
          </svg>
          <span>数学</span>
        </div>
      </div>

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
          <span class="hl-line">让AI成为</span>
          <span class="hl-line hl-neon">每位老师</span>
          <span class="hl-line">最好的陪练</span>
        </h1>

        <p class="tagline">
          上传教案，模拟真实课堂<br>
          获取定制化教学反馈报告
        </p>
      </div>
    </section>

    <section class="right-panel">
      <div class="glass-card">
        <div class="tab-bar">
          <button :class="['tab-btn', { active: mode === 'login' }]" @click="switchMode('login')">登录</button>
          <button :class="['tab-btn', { active: mode === 'register' }]" @click="switchMode('register')">注册</button>
          <button :class="['tab-btn', { active: mode === 'forgot' }]" @click="switchMode('forgot')">找回密码</button>
        </div>

        <p v-if="mode !== 'login'" class="mode-hint">
          {{ modeHint }}
        </p>

        <p v-if="successMsg" class="msg-ok">{{ successMsg }}</p>
        <p v-if="errorMsg" class="msg-err">{{ errorMsg }}</p>

        <form v-if="mode === 'login'" class="form" @submit.prevent="doLogin">
          <div class="form-group">
            <label>邮箱</label>
            <input
              v-model.trim="loginForm.email"
              type="email"
              placeholder="teacher@example.com"
              autocomplete="email"
              required
            />
          </div>

          <div class="form-group">
            <label>密码</label>
            <div class="input-wrap">
              <input
                v-model="loginForm.password"
                :type="showLoginPwd ? 'text' : 'password'"
                placeholder="请输入密码"
                autocomplete="current-password"
                required
              />
              <button type="button" class="eye-btn" @click="showLoginPwd = !showLoginPwd" tabindex="-1">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <template v-if="!showLoginPwd">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </template>
                  <template v-else>
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                    <line x1="1" y1="1" x2="23" y2="23"/>
                  </template>
                </svg>
              </button>
            </div>
          </div>

          <button type="submit" class="submit-btn" :disabled="submitting">
            <span v-if="submitting" class="btn-spinner"></span>
            {{ submitting ? '登录中...' : '登录' }}
          </button>

          <p class="form-footer">
            还没有账号?
            <button type="button" class="link-btn" @click="switchMode('register')">立即注册</button>
          </p>
          <p class="form-footer compact">
            忘记密码?
            <button type="button" class="link-btn" @click="switchMode('forgot')">立即重置</button>
          </p>
        </form>

        <form v-else-if="mode === 'register'" class="form" @submit.prevent="registerStepTwo ? completeRegisterFlow() : sendRegisterCodeStep()">
          <div class="form-group">
            <label>邮箱</label>
            <input
              v-model.trim="registerForm.email"
              type="email"
              placeholder="请输入注册邮箱"
              autocomplete="email"
              :disabled="registerStepTwo"
              required
            />
          </div>

          <template v-if="registerStepTwo">
            <p class="step-hint">
              验证码已发送到 <strong>{{ registerForm.email }}</strong>，请输入验证码并设置账号信息。
            </p>

            <div class="form-group">
              <label>验证码</label>
              <input
                v-model.trim="registerForm.code"
                inputmode="numeric"
                maxlength="6"
                placeholder="6 位数字验证码"
                autocomplete="one-time-code"
                required
              />
            </div>

            <div class="form-group">
              <label>姓名</label>
              <input
                v-model.trim="registerForm.displayName"
                type="text"
                placeholder="课堂中显示的姓名"
                autocomplete="name"
                required
              />
            </div>

            <div class="form-group">
              <label>密码</label>
              <div class="input-wrap">
                <input
                  v-model="registerForm.password"
                  :type="showRegisterPwd ? 'text' : 'password'"
                  placeholder="至少 8 位"
                  autocomplete="new-password"
                  required
                />
                <button type="button" class="eye-btn" @click="showRegisterPwd = !showRegisterPwd" tabindex="-1">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <template v-if="!showRegisterPwd">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                      <circle cx="12" cy="12" r="3"/>
                    </template>
                    <template v-else>
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                      <line x1="1" y1="1" x2="23" y2="23"/>
                    </template>
                  </svg>
                </button>
              </div>
            </div>

            <div class="form-group">
              <label>确认密码</label>
              <div class="input-wrap">
                <input
                  v-model="registerForm.confirm"
                  :type="showRegisterPwd2 ? 'text' : 'password'"
                  placeholder="再次输入密码"
                  autocomplete="new-password"
                  required
                />
                <button type="button" class="eye-btn" @click="showRegisterPwd2 = !showRegisterPwd2" tabindex="-1">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <template v-if="!showRegisterPwd2">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                      <circle cx="12" cy="12" r="3"/>
                    </template>
                    <template v-else>
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                      <line x1="1" y1="1" x2="23" y2="23"/>
                    </template>
                  </svg>
                </button>
              </div>
              <p v-if="registerForm.confirm && registerForm.password !== registerForm.confirm" class="field-warn">
                两次输入的密码不一致
              </p>
            </div>

            <div class="action-row">
              <button type="button" class="secondary-btn" :disabled="submitting" @click="backToRegisterEmail">返回上一步</button>
              <button type="button" class="secondary-btn" :disabled="submitting" @click="resendRegisterCodeStep">重新发送</button>
            </div>
          </template>

          <button
            type="submit"
            class="submit-btn"
            :disabled="submitting || (registerStepTwo && !!registerForm.confirm && registerForm.password !== registerForm.confirm)"
          >
            <span v-if="submitting" class="btn-spinner"></span>
            {{ submitting ? (registerStepTwo ? '注册中...' : '发送中...') : (registerStepTwo ? '完成注册' : '发送验证码') }}
          </button>

          <p class="form-footer">
            已有账号?
            <button type="button" class="link-btn" @click="switchMode('login')">直接登录</button>
          </p>
        </form>

        <form v-else class="form" @submit.prevent="resetStepTwo ? completeResetFlow() : sendResetCodeStep()">
          <div class="form-group">
            <label>邮箱</label>
            <input
              v-model.trim="resetForm.email"
              type="email"
              placeholder="请输入注册邮箱"
              autocomplete="email"
              :disabled="resetStepTwo"
              required
            />
          </div>

          <template v-if="resetStepTwo">
            <p class="step-hint">
              验证码已发送到 <strong>{{ resetForm.email }}</strong>，验证通过后会自动登录。
            </p>

            <div class="form-group">
              <label>验证码</label>
              <input
                v-model.trim="resetForm.code"
                inputmode="numeric"
                maxlength="6"
                placeholder="6 位数字验证码"
                autocomplete="one-time-code"
                required
              />
            </div>

            <div class="form-group">
              <label>新密码</label>
              <div class="input-wrap">
                <input
                  v-model="resetForm.password"
                  :type="showResetPwd ? 'text' : 'password'"
                  placeholder="至少 8 位"
                  autocomplete="new-password"
                  required
                />
                <button type="button" class="eye-btn" @click="showResetPwd = !showResetPwd" tabindex="-1">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <template v-if="!showResetPwd">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                      <circle cx="12" cy="12" r="3"/>
                    </template>
                    <template v-else>
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                      <line x1="1" y1="1" x2="23" y2="23"/>
                    </template>
                  </svg>
                </button>
              </div>
            </div>

            <div class="form-group">
              <label>确认新密码</label>
              <div class="input-wrap">
                <input
                  v-model="resetForm.confirm"
                  :type="showResetPwd2 ? 'text' : 'password'"
                  placeholder="再次输入新密码"
                  autocomplete="new-password"
                  required
                />
                <button type="button" class="eye-btn" @click="showResetPwd2 = !showResetPwd2" tabindex="-1">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <template v-if="!showResetPwd2">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                      <circle cx="12" cy="12" r="3"/>
                    </template>
                    <template v-else>
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                      <line x1="1" y1="1" x2="23" y2="23"/>
                    </template>
                  </svg>
                </button>
              </div>
              <p v-if="resetForm.confirm && resetForm.password !== resetForm.confirm" class="field-warn">
                两次输入的密码不一致
              </p>
            </div>

            <div class="action-row">
              <button type="button" class="secondary-btn" :disabled="submitting" @click="backToResetEmail">返回上一步</button>
              <button type="button" class="secondary-btn" :disabled="submitting" @click="resendResetCodeStep">重新发送</button>
            </div>
          </template>

          <button
            type="submit"
            class="submit-btn"
            :disabled="submitting || (resetStepTwo && !!resetForm.confirm && resetForm.password !== resetForm.confirm)"
          >
            <span v-if="submitting" class="btn-spinner"></span>
            {{ submitting ? (resetStepTwo ? '重置中...' : '发送中...') : (resetStepTwo ? '完成重置' : '发送验证码') }}
          </button>

          <p class="form-footer">
            想起密码了?
            <button type="button" class="link-btn" @click="switchMode('login')">返回登录</button>
          </p>
        </form>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/authStore.js'

const router = useRouter()
const auth = useAuthStore()

const mode = ref('login')
const submitting = ref(false)
const errorMsg = ref('')
const successMsg = ref('')

const showLoginPwd = ref(false)
const showRegisterPwd = ref(false)
const showRegisterPwd2 = ref(false)
const showResetPwd = ref(false)
const showResetPwd2 = ref(false)

const registerPhase = ref('request')
const resetPhase = ref('request')

const loginForm = ref({
  email: '',
  password: '',
})

const registerForm = ref({
  email: '',
  code: '',
  displayName: '',
  password: '',
  confirm: '',
})

const resetForm = ref({
  email: '',
  code: '',
  password: '',
  confirm: '',
})

const registerStepTwo = computed(() => registerPhase.value === 'verify')
const resetStepTwo = computed(() => resetPhase.value === 'verify')

const modeHint = computed(() => {
  if (mode.value === 'register') {
    return registerStepTwo.value
      ? '输入验证码并设置姓名与密码，完成后会自动登录。'
      : '输入邮箱，系统会向你的收件箱发送注册验证码。'
  }
  if (mode.value === 'forgot') {
    return resetStepTwo.value
      ? '完成新密码设置后会撤销旧会话并自动登录。'
      : '输入注册邮箱，系统会发送重置密码验证码。'
  }
  return ''
})

function resetMessages() {
  errorMsg.value = ''
  successMsg.value = ''
}

function resetVisibility() {
  showLoginPwd.value = false
  showRegisterPwd.value = false
  showRegisterPwd2.value = false
  showResetPwd.value = false
  showResetPwd2.value = false
}

function switchMode(nextMode) {
  mode.value = nextMode
  resetMessages()
  resetVisibility()
  if (nextMode !== 'register') {
    registerPhase.value = 'request'
    registerForm.value.code = ''
    registerForm.value.password = ''
    registerForm.value.confirm = ''
  }
  if (nextMode !== 'forgot') {
    resetPhase.value = 'request'
    resetForm.value.code = ''
    resetForm.value.password = ''
    resetForm.value.confirm = ''
  }
}

function validatePasswords(password, confirm) {
  if (password !== confirm) {
    throw new Error('两次输入的密码不一致')
  }
  if (password.length < 8) {
    throw new Error('密码至少需要 8 位')
  }
}

async function doLogin() {
  resetMessages()
  submitting.value = true
  try {
    await auth.login(loginForm.value.email, loginForm.value.password)
    await router.push('/setup')
  } catch (error) {
    errorMsg.value = error.message || '登录失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}

async function sendRegisterCodeStep() {
  resetMessages()
  submitting.value = true
  try {
    await auth.sendRegisterCode(registerForm.value.email)
    registerPhase.value = 'verify'
    successMsg.value = '验证码已发送，请查收邮箱。'
  } catch (error) {
    errorMsg.value = error.message || '验证码发送失败'
  } finally {
    submitting.value = false
  }
}

async function resendRegisterCodeStep() {
  await sendRegisterCodeStep()
}

function backToRegisterEmail() {
  resetMessages()
  registerPhase.value = 'request'
  registerForm.value.code = ''
  registerForm.value.password = ''
  registerForm.value.confirm = ''
}

async function completeRegisterFlow() {
  resetMessages()
  submitting.value = true
  try {
    validatePasswords(registerForm.value.password, registerForm.value.confirm)
    const verified = await auth.verifyRegisterCode(registerForm.value.email, registerForm.value.code)
    await auth.completeRegister(
      registerForm.value.email,
      registerForm.value.displayName,
      registerForm.value.password,
      verified.verification_token,
    )
    await router.push('/setup')
  } catch (error) {
    errorMsg.value = error.message || '注册失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}

async function sendResetCodeStep() {
  resetMessages()
  submitting.value = true
  try {
    await auth.sendResetCode(resetForm.value.email)
    resetPhase.value = 'verify'
    successMsg.value = '验证码已发送，请查收邮箱。'
  } catch (error) {
    errorMsg.value = error.message || '验证码发送失败'
  } finally {
    submitting.value = false
  }
}

async function resendResetCodeStep() {
  await sendResetCodeStep()
}

function backToResetEmail() {
  resetMessages()
  resetPhase.value = 'request'
  resetForm.value.code = ''
  resetForm.value.password = ''
  resetForm.value.confirm = ''
}

async function completeResetFlow() {
  resetMessages()
  submitting.value = true
  try {
    validatePasswords(resetForm.value.password, resetForm.value.confirm)
    const verified = await auth.verifyResetCode(resetForm.value.email, resetForm.value.code)
    await auth.completeReset(resetForm.value.email, resetForm.value.password, verified.verification_token)
    await router.push('/setup')
  } catch (error) {
    errorMsg.value = error.message || '密码重置失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Caveat:wght@400;600;700&display=swap');

.login-page {
  position: relative;
  display: flex;
  flex: 1;
  min-width: 0;
  width: 100%;
  min-height: 100vh;
  padding-right: 72px;
  overflow: hidden;
  background: #020817;
  color: rgba(255, 255, 255, 0.95);
}

.global-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
  background:
    radial-gradient(ellipse at 20% 30%, #1637a3 0%, transparent 52%),
    radial-gradient(ellipse at 82% 72%, rgba(88, 28, 135, 0.72) 0%, transparent 46%),
    linear-gradient(160deg, #071127 0%, #090e1e 40%, #0d0824 72%, #050714 100%);
}

.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(34, 211, 238, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(34, 211, 238, 0.035) 1px, transparent 1px);
  background-size: 52px 52px;
}

.glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  pointer-events: none;
}

.g1 {
  width: 500px;
  height: 500px;
  background: rgba(37, 99, 235, 0.28);
  top: -130px;
  left: -80px;
  animation: glowPulse 7s ease-in-out infinite;
}

.g2 {
  width: 420px;
  height: 420px;
  background: rgba(109, 40, 217, 0.24);
  bottom: -120px;
  right: -40px;
  animation: glowPulse 9s ease-in-out infinite reverse;
}

.g3 {
  width: 320px;
  height: 320px;
  background: rgba(6, 182, 212, 0.12);
  top: 38%;
  left: 46%;
  animation: glowPulse 11s ease-in-out infinite 2s;
}

.g4 {
  width: 220px;
  height: 220px;
  background: rgba(167, 139, 250, 0.1);
  top: 16%;
  right: 34%;
  animation: glowPulse 8s ease-in-out infinite 1s;
}

.scan-lines {
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    to bottom,
    transparent 0,
    transparent 3px,
    rgba(0, 0, 0, 0.055) 3px,
    rgba(0, 0, 0, 0.055) 4px
  );
}

.left-panel {
  flex: 1;
  min-width: 0;
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.neural-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0.48;
  z-index: 1;
}

.edge {
  stroke: rgba(34, 211, 238, 0.16);
  stroke-width: 1;
}

.node {
  stroke-width: 1.5;
  animation: nodePulse 3.5s ease-in-out infinite;
}

.node-cyan {
  fill: rgba(14, 116, 144, 0.58);
  stroke: rgba(34, 211, 238, 0.76);
}

.node-purple {
  fill: rgba(109, 40, 217, 0.58);
  stroke: rgba(167, 139, 250, 0.76);
}

.node-output {
  fill: rgba(5, 150, 105, 0.58);
  stroke: rgba(52, 211, 153, 0.88);
  animation-duration: 2.5s;
}

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

.subjects {
  position: absolute;
  inset: 0;
  z-index: 3;
  pointer-events: none;
}

.sym {
  position: absolute;
  font-family: Georgia, serif;
  font-style: italic;
  animation: symFloat 9s ease-in-out infinite;
}

.sym-cyan {
  color: rgba(34, 211, 238, 0.45);
  text-shadow: 0 0 12px rgba(34, 211, 238, 0.55);
}

.sym-purple {
  color: rgba(168, 85, 247, 0.45);
  text-shadow: 0 0 12px rgba(168, 85, 247, 0.55);
}

.sym-green {
  color: rgba(52, 211, 153, 0.42);
  text-shadow: 0 0 12px rgba(52, 211, 153, 0.5);
}

.s1 { font-size: 28px; top: 12%; left: 5%; animation-delay: 0s; }
.s2 { font-size: 22px; top: 30%; left: 82%; animation-delay: 1.5s; }
.s3 { font-size: 26px; top: 60%; left: 4%; animation-delay: 3s; }
.s4 { font-size: 30px; top: 20%; left: 70%; animation-delay: 0.8s; }
.s5 { font-size: 18px; top: 72%; left: 78%; animation-delay: 2.2s; }
.s6 { font-size: 24px; top: 8%; left: 50%; animation-delay: 4s; }
.s7 { font-size: 14px; top: 82%; left: 55%; animation-delay: 1.8s; font-family: monospace; font-style: normal; letter-spacing: 1px; }

.icon-chip {
  position: absolute;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 11px;
  background: rgba(2, 8, 23, 0.62);
  border-radius: 20px;
  animation: chipFloat 10s ease-in-out infinite;
  backdrop-filter: blur(6px);
}

.icon-chip span {
  font-size: 11px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.62);
}

.chip-letter {
  font-size: 16px !important;
  font-weight: 900 !important;
  font-style: italic;
  color: #fbbf24 !important;
  text-shadow: 0 0 10px rgba(251, 191, 36, 0.7);
  line-height: 1;
}

.ic1 {
  top: 3%;
  left: 35%;
  border: 1px solid rgba(251, 191, 36, 0.3);
  box-shadow: 0 0 12px rgba(251, 191, 36, 0.15);
  animation-delay: 3.5s;
  animation-duration: 10s;
}

.ic2 {
  top: 5%;
  left: 64%;
  border: 1px solid rgba(34, 211, 238, 0.3);
  box-shadow: 0 0 12px rgba(34, 211, 238, 0.15);
  animation-delay: 0s;
  animation-duration: 9s;
}

.ic3 {
  top: 15%;
  left: 76%;
  border: 1px solid rgba(52, 211, 153, 0.3);
  box-shadow: 0 0 12px rgba(52, 211, 153, 0.15);
  animation-delay: 2s;
  animation-duration: 8.5s;
}

.ic4 {
  top: 26%;
  left: 74%;
  border: 1px solid rgba(52, 211, 153, 0.3);
  box-shadow: 0 0 12px rgba(52, 211, 153, 0.15);
  animation-delay: 2.5s;
  animation-duration: 8s;
}

.ic5 {
  top: 36%;
  left: 62%;
  border: 1px solid rgba(168, 85, 247, 0.3);
  box-shadow: 0 0 12px rgba(168, 85, 247, 0.15);
  animation-delay: 4.2s;
  animation-duration: 11s;
}

.ic6 {
  top: 55%;
  left: 80%;
  border: 1px solid rgba(96, 165, 250, 0.3);
  box-shadow: 0 0 12px rgba(96, 165, 250, 0.15);
  animation-delay: 1.8s;
  animation-duration: 9s;
}

.ic7 {
  top: 68%;
  left: 56%;
  border: 1px solid rgba(249, 115, 22, 0.3);
  box-shadow: 0 0 12px rgba(249, 115, 22, 0.15);
  animation-delay: 1.5s;
  animation-duration: 10s;
}

.ic8 {
  top: 48%;
  left: 5%;
  border: 1px solid rgba(244, 114, 182, 0.3);
  box-shadow: 0 0 12px rgba(244, 114, 182, 0.15);
  animation-delay: 0.7s;
  animation-duration: 12s;
}

.ic9 {
  top: 72%;
  left: 4%;
  border: 1px solid rgba(168, 85, 247, 0.3);
  box-shadow: 0 0 12px rgba(168, 85, 247, 0.15);
  animation-delay: 1.2s;
  animation-duration: 11s;
}

.left-content {
  position: relative;
  z-index: 4;
  padding: 0 56px;
  max-width: 560px;
  width: 100%;
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
  background: rgba(37, 99, 235, 0.35);
  border: 1px solid rgba(34, 211, 238, 0.4);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 22px rgba(34, 211, 238, 0.25);
  backdrop-filter: blur(8px);
}

.brand-name {
  font-size: 32px;
  font-weight: 800;
  letter-spacing: -0.5px;
  color: rgba(255, 255, 255, 0.95);
  text-shadow: 0 0 24px rgba(34, 211, 238, 0.4);
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
  color: rgba(255, 255, 255, 0.95);
  text-shadow: 0 2px 20px rgba(0, 0, 0, 0.6), 0 0 40px rgba(255, 255, 255, 0.06);
}

.hl-neon {
  background: linear-gradient(90deg, #22D3EE, #A855F7, #22D3EE);
  background-size: 200% auto;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  animation: textShine 4s linear infinite;
  text-shadow: none;
}

.tagline {
  font-size: 15px;
  color: rgba(255, 255, 255, 0.72);
  line-height: 1.85;
  text-shadow: 0 1px 16px rgba(0, 0, 0, 0.8), 0 0 30px rgba(34, 211, 238, 0.15);
  font-weight: 400;
  letter-spacing: 0.4px;
}

.right-panel {
  width: 420px;
  min-width: 420px;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  position: relative;
  z-index: 5;
  padding: 40px 0 40px 0;
  margin-left: -180px;
}

.glass-card {
  width: 100%;
  position: relative;
  background: rgba(5, 12, 35, 0.72);
  backdrop-filter: blur(28px) saturate(180%);
  border-radius: 22px;
  border: 1px solid rgba(34, 211, 238, 0.22);
  box-shadow:
    0 0 0 1px rgba(168, 85, 247, 0.12),
    0 24px 64px rgba(0, 0, 0, 0.65),
    0 0 40px rgba(34, 211, 238, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
  padding: 36px 34px 30px;
  overflow: hidden;
}

.tab-bar {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0;
  padding: 3px;
  margin-bottom: 28px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.tab-btn {
  border: none;
  padding: 9px 8px;
  border-radius: 10px;
  background: transparent;
  color: rgba(255, 255, 255, 0.4);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s;
}

.tab-btn.active {
  background: rgba(34, 211, 238, 0.12);
  color: #22D3EE;
  box-shadow: 0 0 16px rgba(34, 211, 238, 0.2), inset 0 0 12px rgba(34, 211, 238, 0.05);
  border: 1px solid rgba(34, 211, 238, 0.25);
}

.mode-hint {
  margin: -8px 0 16px;
  color: rgba(226, 232, 240, 0.66);
  font-size: 13px;
  line-height: 1.6;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.form-group label {
  font-size: 12px;
  font-weight: 700;
  color: rgba(226, 232, 240, 0.58);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.form-group input {
  width: 100%;
  height: 54px;
  padding: 0 18px;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(255, 255, 255, 0.06);
  color: #f8fafc;
  font-size: 15px;
  outline: none;
  transition: 0.18s ease;
}

.form-group input::placeholder {
  color: rgba(226, 232, 240, 0.26);
}

.form-group input:focus {
  border-color: rgba(103, 232, 249, 0.7);
  background: rgba(34, 211, 238, 0.08);
  box-shadow: 0 0 0 4px rgba(34, 211, 238, 0.1);
}

.input-wrap {
  position: relative;
}

.input-wrap input {
  padding-right: 48px;
}

.eye-btn {
  position: absolute;
  top: 50%;
  right: 14px;
  transform: translateY(-50%);
  border: none;
  background: transparent;
  color: rgba(226, 232, 240, 0.34);
  cursor: pointer;
  display: flex;
  align-items: center;
}

.eye-btn:hover {
  color: #67e8f9;
}

.step-hint {
  margin: -6px 0 0;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid rgba(125, 211, 252, 0.14);
  color: rgba(226, 232, 240, 0.76);
  font-size: 13px;
  line-height: 1.6;
}

.step-hint strong {
  color: #f8fafc;
}

.field-warn,
.msg-err,
.msg-ok {
  font-size: 12.5px;
  border-radius: 10px;
  padding: 10px 12px;
}

.field-warn {
  margin: -6px 0 0;
  color: #fcd34d;
  background: rgba(234, 179, 8, 0.1);
  border: 1px solid rgba(234, 179, 8, 0.18);
}

.msg-err {
  margin: -4px 0 -2px;
  color: #fecaca;
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.22);
}

.msg-ok {
  margin: -4px 0 -2px;
  color: #86efac;
  background: rgba(34, 197, 94, 0.12);
  border: 1px solid rgba(34, 197, 94, 0.22);
}

.submit-btn,
.secondary-btn {
  height: 56px;
  border: none;
  border-radius: 15px;
  font-size: 15px;
  font-weight: 800;
  cursor: pointer;
  transition: 0.2s ease;
}

.submit-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 2px;
  color: #fff;
  background: linear-gradient(135deg, #2950d9 0%, #7c3aed 100%);
  box-shadow: 0 18px 36px rgba(59, 130, 246, 0.2);
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 20px 42px rgba(124, 58, 237, 0.28);
}

.secondary-btn {
  color: rgba(226, 232, 240, 0.84);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.secondary-btn:hover:not(:disabled) {
  border-color: rgba(125, 211, 252, 0.3);
  color: #f8fafc;
}

.submit-btn:disabled,
.secondary-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.btn-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 999px;
  animation: spin 0.7s linear infinite;
}

.form-footer {
  margin: -2px 0 0;
  text-align: center;
  color: rgba(226, 232, 240, 0.38);
  font-size: 13px;
}

.form-footer.compact {
  margin-top: -10px;
}

.link-btn {
  border: none;
  background: transparent;
  padding: 0;
  color: #22d3ee;
  font-weight: 700;
  cursor: pointer;
}

.link-btn:hover {
  color: #67e8f9;
}

@keyframes glowPulse {
  0%, 100% { opacity: 0.6; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.12); }
}

@keyframes nodePulse {
  0%, 100% { opacity: 0.65; }
  50% { opacity: 1; }
}

@keyframes symFloat {
  0%, 100% { transform: translateY(0) rotate(-4deg); opacity: 0.5; }
  33% { transform: translateY(-16px) rotate(3deg); opacity: 0.8; }
  66% { transform: translateY(-6px) rotate(-2deg); opacity: 0.6; }
}

@keyframes textShine {
  to { background-position: 200% center; }
}

@keyframes chipFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-12px); }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 1440px) {
  .hl-line {
    font-size: 74px;
  }

  .right-panel {
    width: 420px;
    min-width: 420px;
    margin-left: -120px;
  }
}

@media (max-width: 1180px) {
  .login-page {
    padding-right: 0;
    flex-direction: column;
  }

  .left-panel {
    min-height: 58vh;
  }

  .left-content {
    width: min(600px, calc(100% - 48px));
    max-width: none;
    padding: 0 24px;
    margin: 12px auto 0;
  }

  .classroom-svg {
    transform: translateX(-50%);
    width: min(90vw, 760px);
  }

  .right-panel {
    width: auto;
    min-width: 0;
    margin-left: 0;
    padding: 0 20px 28px;
  }

  .glass-card {
    max-width: 480px;
  }
}

@media (max-width: 820px) {
  .subjects,
  .classroom-svg {
    display: none;
  }

  .left-panel {
    min-height: 46vh;
  }

  .brand-logo {
    width: 60px;
    height: 60px;
  }

  .brand-name {
    font-size: 34px;
  }

  .hl-line {
    font-size: 56px;
    letter-spacing: -2px;
  }

  .tagline {
    font-size: 16px;
  }

  .glass-card {
    padding: 28px 20px 24px;
  }

  .tab-bar {
    grid-template-columns: 1fr;
  }

  .action-row {
    grid-template-columns: 1fr;
  }
}
</style>
