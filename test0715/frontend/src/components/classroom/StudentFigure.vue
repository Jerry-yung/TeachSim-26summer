<template>
  <div class="student-wrap" :class="[behavior, { active }]" :style="{ '--c': color }">
    <svg class="fig-svg" viewBox="0 0 100 158" xmlns="http://www.w3.org/2000/svg">

      <!-- ── DESK ── -->
      <rect class="desk-top" x="2" y="108" width="96" height="6" rx="3"/>
      <line class="desk-leg" x1="10" y1="114" x2="8"  y2="150"/>
      <line class="desk-leg" x1="90" y1="114" x2="92" y2="150"/>

      <!-- notebook on desk (writing only) -->
      <g v-if="behavior === 'writing'" class="notebook-g">
        <rect class="notebook" x="14" y="97" width="40" height="12" rx="2"/>
        <line class="nb-rule" x1="18" y1="102" x2="51" y2="102"/>
        <line class="nb-rule" x1="18" y1="106" x2="47" y2="106"/>
      </g>

      <!-- ── CHAIR ── -->
      <rect class="chair" x="28" y="103" width="44" height="6" rx="3"/>

      <!-- ── LEGS ── -->
      <line class="limb" x1="40" y1="109" x2="36" y2="148"/>
      <line class="limb" x1="60" y1="109" x2="64" y2="148"/>
      <ellipse class="shoe" cx="34" cy="150" rx="9"  ry="4.5"/>
      <ellipse class="shoe" cx="66" cy="150" rx="9"  ry="4.5"/>

      <!-- ── TORSO ── -->
      <rect class="torso" x="33" y="60" width="34" height="46" rx="11"/>

      <!-- ── LEFT ARM (rests on desk) ── -->
      <line class="limb" x1="33" y1="74" x2="15" y2="107"/>
      <ellipse class="hand" cx="14" cy="109" rx="6" ry="5"/>

      <!-- ── RIGHT ARM ── -->
      <g class="right-arm-g" :class="{ 'anim-write': behavior === 'writing' }">
        <line class="limb" x1="67" y1="74" x2="85" y2="107"/>
        <ellipse class="hand" cx="86" cy="109" rx="6" ry="5"/>
        <!-- pencil when writing -->
        <g v-if="behavior === 'writing'" transform="translate(86,100) rotate(-22)">
          <rect x="-2.5" y="-20" width="5" height="24" rx="1.5" fill="#FBBF24"/>
          <polygon points="-2.5,4 2.5,4 0,10" fill="#F97316"/>
          <rect x="-2.5" y="-24" width="5" height="4" rx="1" fill="#94A3B8"/>
        </g>
      </g>

      <!-- ── HEAD GROUP (pivot = neck-torso junction at SVG 50,60) ── -->
      <g class="head-g" :class="behavior">
        <!-- neck -->
        <rect class="neck" x="44" y="42" width="12" height="20" rx="5"/>
        <!-- skull -->
        <circle class="skull" cx="50" cy="28" r="22"/>
        <!-- hair -->
        <path class="hair"
              d="M28,28 Q28,4 50,2 Q72,4 72,28 Q70,14 60,10 Q50,8 40,10 Q30,14 28,28 Z"/>
        <!-- ears -->
        <ellipse class="ear" cx="28" cy="28" rx="5.5" ry="7"/>
        <ellipse class="ear" cx="72" cy="28" rx="5.5" ry="7"/>
        <!-- eyebrows -->
        <path class="brow" d="M36,16 Q42,13 48,16"/>
        <path class="brow" d="M52,16 Q58,13 64,16"/>

        <!-- EYES: normal / writing / dreaming -->
        <g v-if="behavior !== 'dozing'">
          <ellipse class="eye-white" :cx="40 + eyeDx"  :cy="26 + eyeDy" rx="5" ry="5.5"/>
          <circle  class="pupil"     :cx="41 + eyeDx"  :cy="27 + eyeDy" r="2.5"/>
          <ellipse class="eye-white" :cx="60 + eyeDx"  :cy="26 + eyeDy" rx="5" ry="5.5"/>
          <circle  class="pupil"     :cx="61 + eyeDx"  :cy="27 + eyeDy" r="2.5"/>
        </g>
        <!-- EYES: dozing (closed curves) -->
        <g v-else class="doze-eyes">
          <path d="M35,26 Q40,30 45,26" class="eye-shut"/>
          <path d="M55,26 Q60,30 65,26" class="eye-shut"/>
        </g>

        <!-- MOUTH -->
        <path class="mouth" :d="mouthD"/>
      </g>

      <!-- ══ BEHAVIOR OVERLAYS ══ -->

      <!-- DOZING: ZZZ -->
      <g v-if="behavior === 'dozing'" class="zzz-grp">
        <text class="zzz za" x="73" y="24">Z</text>
        <text class="zzz zb" x="81" y="14">Z</text>
        <text class="zzz zc" x="88" y="6">Z</text>
      </g>

      <!-- DREAMING: thought cloud -->
      <g v-if="behavior === 'dreaming'" class="dream-grp">
        <circle class="cl-dot d1" cx="70" cy="22" r="3"/>
        <circle class="cl-dot d2" cx="78" cy="14" r="4.5"/>
        <circle class="cl-body cb1" cx="90" cy="8"  r="9"/>
        <circle class="cl-body cb2" cx="100" cy="13" r="7"/>
        <circle class="cl-body cb3" cx="96" cy="2"  r="6.5"/>
        <text class="dream-icon" x="87" y="12">✦</text>
      </g>

      <!-- WHISPER-LEFT: sound waves going right -->
      <g v-if="behavior === 'whisper-left'" class="wave-grp">
        <path class="wv w1" d="M67,22 Q74,16 81,22"/>
        <path class="wv w2" d="M71,30 Q80,22 89,30"/>
      </g>

      <!-- WHISPER-RIGHT: sound waves going left -->
      <g v-if="behavior === 'whisper-right'" class="wave-grp">
        <path class="wv w1" d="M33,22 Q26,16 19,22"/>
        <path class="wv w2" d="M29,30 Q20,22 11,30"/>
      </g>

      <!-- Active glow ring (when student is speaking) -->
      <circle v-if="active" class="active-ring" cx="50" cy="28" r="27"/>
    </svg>
    <div class="s-label">{{ name }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  behavior: { type: String, default: 'dreaming' },
  color:    { type: String, default: '#22D3EE' },
  name:     { type: String, default: '学生' },
  active:   { type: Boolean, default: false },
})

// Eye offset per behavior
const eyeDx = computed(() => {
  if (props.behavior === 'dreaming')      return -2
  if (props.behavior === 'writing')       return 0
  if (props.behavior === 'whisper-left')  return 3
  if (props.behavior === 'whisper-right') return -3
  return 1
})
const eyeDy = computed(() => {
  if (props.behavior === 'writing')  return 3
  if (props.behavior === 'dreaming') return -3
  return 0
})

const mouthD = computed(() => {
  if (props.behavior === 'dozing')                              return 'M43,38 Q50,42 57,38'  // open-ish
  if (props.behavior === 'dreaming')                            return 'M44,37 Q50,35 56,37'  // neutral
  if (props.behavior === 'whisper-left' || props.behavior === 'whisper-right')
                                                                return 'M44,36 Q50,40 56,36'  // talking open
  return 'M44,37 Q50,40 56,37'  // gentle smile
})
</script>

<style scoped>
/* ── Layout ── */
.student-wrap {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  min-height: 100%;
}
.fig-svg {
  width: 100%;
  height: auto;
  overflow: visible;
}
.s-label {
  position: absolute;
  top: 2px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2;
  font-size: 12px;
  font-weight: 700;
  color: #e2e8f0;
  letter-spacing: 0.4px;
  line-height: 1;
  padding: 5px 9px;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--c) 48%, transparent);
  background: color-mix(in srgb, var(--c) 18%, #0b1220);
  text-shadow: 0 0 8px color-mix(in srgb, var(--c) 65%, transparent);
  box-shadow: 0 0 10px color-mix(in srgb, var(--c) 30%, transparent);
  white-space: nowrap;
}

/* ── Base SVG element styles ── */
.desk-top { fill: rgba(34,211,238,0.12); stroke: rgba(34,211,238,0.3); stroke-width: 1; }
.desk-leg { stroke: rgba(34,211,238,0.2); stroke-width: 1.5; }
.notebook { fill: rgba(255,255,255,0.08); stroke: rgba(255,255,255,0.25); stroke-width: 1; }
.nb-rule  { stroke: rgba(255,255,255,0.18); stroke-width: 0.8; }
.chair    { fill: rgba(100,116,139,0.25); stroke: rgba(148,163,184,0.3); stroke-width: 1; }
.limb     { stroke: var(--c); stroke-width: 3.5; stroke-linecap: round; opacity: 0.85; }
.shoe     { fill: var(--c); opacity: 0.5; }
.torso    { fill: var(--c); opacity: 0.3; stroke: var(--c); stroke-width: 1; }
.hand     { fill: var(--c); opacity: 0.55; }
.neck     { fill: var(--c); opacity: 0.3; }
.skull    { fill: var(--c); opacity: 0.28; stroke: var(--c); stroke-width: 1.5; }
.hair     { fill: var(--c); opacity: 0.65; }
.ear      { fill: var(--c); opacity: 0.3; stroke: var(--c); stroke-width: 1; }
.brow     { fill: none; stroke: var(--c); stroke-width: 1.5; stroke-linecap: round; opacity: 0.7; }
.eye-white{ fill: rgba(255,255,255,0.88); }
.pupil    { fill: #0F172A; }
.eye-shut { fill: none; stroke: var(--c); stroke-width: 2; stroke-linecap: round; }
.mouth    { fill: none; stroke: var(--c); stroke-width: 1.8; stroke-linecap: round; opacity: 0.8; }

/* Active glow ring */
.active-ring {
  fill: none;
  stroke: var(--c);
  stroke-width: 2;
  opacity: 0;
  animation: ring-pulse 1.2s ease-in-out infinite;
}
@keyframes ring-pulse {
  0%,100% { opacity: 0; transform-box: fill-box; transform-origin: center; transform: scale(1); }
  50%      { opacity: 0.8; transform: scale(1.08); }
}

/* ── HEAD GROUP ANIMATIONS ── */
.head-g {
  transform: translate(0, 0);
  transform-origin: 50px 60px;
}

/* WRITING: head tilted down ~38° */
.head-g.writing {
  animation: head-write 5s ease-in-out infinite;
}
@keyframes head-write {
  0%,100% { transform: rotate(38deg); }
  50%      { transform: rotate(40deg); }
}

/* RIGHT ARM writing motion */
.right-arm-g.anim-write {
  transform-origin: 67px 74px;
  animation: arm-write 0.75s ease-in-out infinite;
}
@keyframes arm-write {
  0%,100% { transform: translateX(0)   rotate(0deg); }
  50%      { transform: translateX(6px) rotate(7deg); }
}

/* DREAMING: head tilted sideways */
.head-g.dreaming {
  animation: head-dream 6s ease-in-out infinite;
}
@keyframes head-dream {
  0%,100% { transform: rotate(-14deg); }
  50%      { transform: rotate(-17deg); }
}

/* Dream cloud pulse */
.dream-grp { animation: cloud-pulse 4s ease-in-out infinite; }
.dream-icon { fill: var(--c); font-size: 9px; opacity: 0.9; animation: cloud-pulse 2s ease-in-out infinite; }
@keyframes cloud-pulse {
  0%,100% { opacity: 0.45; transform: scale(0.95); }
  50%      { opacity: 0.80; transform: scale(1.05); }
}
.cl-dot,.cl-body { fill: var(--c); opacity: 0.35; }

/* DOZING: head nods */
.head-g.dozing {
  transform-origin: 50px 60px;
  animation: head-doze 3.5s ease-in-out infinite;
}
@keyframes head-doze {
  0%        { transform: rotate(0deg); }
  30%       { transform: rotate(30deg); }
  62%       { transform: rotate(30deg); }
  80%       { transform: rotate(-5deg); }
  100%      { transform: rotate(0deg); }
}

/* ZZZ */
.zzz { fill: var(--c); font-size: 11px; font-weight: 900; font-family: sans-serif; }
.za  { animation: zzz-rise 2.2s ease-in-out infinite; }
.zb  { animation: zzz-rise 2.2s ease-in-out infinite 0.55s; font-size: 13px; }
.zc  { animation: zzz-rise 2.2s ease-in-out infinite 1.1s;  font-size: 15px; }
@keyframes zzz-rise {
  0%   { opacity: 0;   transform: translate(0,0)      scale(0.5); }
  20%  { opacity: 1; }
  80%  { opacity: 0.7; }
  100% { opacity: 0;   transform: translate(6px,-20px) scale(1.2); }
}

/* WHISPER: lean toward partner */
.head-g.whisper-left {
  transform-origin: 50px 60px;
  animation: whisp-l 2.5s ease-in-out infinite;
}
@keyframes whisp-l {
  0%,100% { transform: rotate(12deg); }
  50%      { transform: rotate(15deg); }
}
.head-g.whisper-right {
  transform-origin: 50px 60px;
  animation: whisp-r 2.5s ease-in-out infinite;
}
@keyframes whisp-r {
  0%,100% { transform: rotate(-12deg); }
  50%      { transform: rotate(-15deg); }
}

/* Whisper waves */
.wv {
  fill: none;
  stroke: var(--c);
  stroke-width: 1.6;
  stroke-linecap: round;
  stroke-dasharray: 14;
  stroke-dashoffset: 14;
}
.w1 { animation: wave-out 1.6s ease-in-out infinite; }
.w2 { animation: wave-out 1.6s ease-in-out infinite 0.45s; }
@keyframes wave-out {
  0%   { stroke-dashoffset:  14; opacity: 0; }
  35%  { opacity: 0.9; }
  100% { stroke-dashoffset: -14; opacity: 0; }
}

/* Active highlight */
.student-wrap.active .skull { stroke-width: 2.5; filter: drop-shadow(0 0 8px var(--c)); }
.student-wrap.active .s-label { font-size: 12px; }
</style>
