<script setup>
import { computed } from 'vue'

const props = defineProps({ block: { type: Object, required: true } })

const W = 840
const H = 300
const PAD = { l: 62, r: 20, t: 16, b: 42 }

const isBar = computed(() => props.block.kind === 'bar')

const points = computed(() => props.block.series.flatMap((s) => s.points))

const domain = computed(() => {
  const xs = points.value.map((p) => p[0])
  const ys = points.value.map((p) => p[1])
  let [x0, x1] = [Math.min(...xs), Math.max(...xs)]
  let [y0, y1] = [Math.min(...ys), Math.max(...ys)]

  if (isBar.value) {
    x0 -= 0.5
    x1 += 0.5
    y0 = Math.min(0, y0)
  }
  if (x1 === x0) x1 = x0 + 1
  const span = y1 - y0 || Math.abs(y1) || 1
  y0 = props.block.y_min ?? y0 - span * 0.08
  y1 = props.block.y_max ?? y1 + span * 0.08
  if (y1 === y0) y1 = y0 + 1
  return { x0, x1, y0, y1 }
})

const sx = (x) => {
  const { x0, x1 } = domain.value
  return PAD.l + ((x - x0) / (x1 - x0)) * (W - PAD.l - PAD.r)
}
const sy = (y) => {
  const { y0, y1 } = domain.value
  return H - PAD.b - ((y - y0) / (y1 - y0)) * (H - PAD.t - PAD.b)
}

function niceTicks(min, max, count) {
  const span = max - min || 1
  const mag = 10 ** Math.floor(Math.log10(span / count))
  const norm = span / count / mag
  const step = (norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10) * mag
  const out = []
  for (let v = Math.ceil(min / step) * step; v <= max + step * 1e-9; v += step) out.push(v)
  return out
}

function fmt(value) {
  const abs = Math.abs(value)
  if (abs >= 1000) return value.toLocaleString('en-US', { maximumFractionDigits: 0 })
  if (abs >= 10) return value.toFixed(1).replace(/\.0$/, '')
  if (abs >= 1) return value.toFixed(2).replace(/0$/, '')
  return Number(value.toPrecision(3)).toString()
}

const yTicks = computed(() => niceTicks(domain.value.y0, domain.value.y1, 5))

const xTicks = computed(() => {
  if (props.block.x_ticks) return props.block.x_ticks.map(([v, label]) => ({ v, label }))
  return niceTicks(domain.value.x0, domain.value.x1, 6).map((v) => ({ v, label: fmt(v) }))
})

const barWidth = computed(() => {
  const n = props.block.series[0]?.points.length || 1
  return Math.max(6, ((W - PAD.l - PAD.r) / n) * 0.55)
})

const zeroY = computed(() => sy(Math.max(domain.value.y0, Math.min(0, domain.value.y1))))

function path(series) {
  return series.points.map((p, i) => `${i ? 'L' : 'M'}${sx(p[0])},${sy(p[1])}`).join(' ')
}
</script>

<template>
  <figure class="chart">
    <figcaption v-if="block.title" class="chart__title">{{ block.title }}</figcaption>

    <div v-if="block.series.length > 1" class="chart__legend">
      <span v-for="s in block.series" :key="s.name" class="chart__key">
        <span class="chart__swatch" :class="`is-${s.color || 'ink'}`" :data-dashed="!!s.dashed" />
        {{ s.name }}
      </span>
    </div>

    <div class="chart__frame">
      <svg :viewBox="`0 0 ${W} ${H}`" role="img" :aria-label="block.title || 'chart'">
        <!-- horizontal rules -->
        <g class="chart__grid">
          <line v-for="t in yTicks" :key="`g${t}`" :x1="PAD.l" :x2="W - PAD.r" :y1="sy(t)" :y2="sy(t)" />
        </g>

        <!-- axes -->
        <g class="chart__axis">
          <line :x1="PAD.l" :x2="PAD.l" :y1="PAD.t" :y2="H - PAD.b" />
          <line :x1="PAD.l" :x2="W - PAD.r" :y1="H - PAD.b" :y2="H - PAD.b" />
        </g>

        <!-- tick labels -->
        <g class="chart__tick">
          <text v-for="t in yTicks" :key="`y${t}`" :x="PAD.l - 8" :y="sy(t) + 4" text-anchor="end">
            {{ fmt(t) }}
          </text>
          <text
            v-for="t in xTicks"
            :key="`x${t.v}`"
            :x="sx(t.v)"
            :y="H - PAD.b + 18"
            text-anchor="middle"
          >
            {{ t.label }}
          </text>
        </g>

        <!-- bars -->
        <g v-if="isBar">
          <g v-for="(s, si) in block.series" :key="`b${si}`" :class="`is-${s.color || 'ink'}`">
            <rect
              v-for="(p, i) in s.points"
              :key="i"
              class="chart__bar"
              :x="sx(p[0]) - barWidth / 2"
              :y="Math.min(sy(p[1]), zeroY)"
              :width="barWidth"
              :height="Math.max(1, Math.abs(zeroY - sy(p[1])))"
            >
              <title>{{ s.name }} @ {{ fmt(p[0]) }} = {{ fmt(p[1]) }}</title>
            </rect>
          </g>
        </g>

        <!-- lines -->
        <g v-else>
          <g v-for="(s, si) in block.series" :key="`l${si}`" :class="`is-${s.color || 'ink'}`">
            <path class="chart__line" :class="{ 'is-dashed': s.dashed }" :d="path(s)" />
            <circle
              v-for="(p, i) in s.points"
              :key="i"
              class="chart__dot"
              :cx="sx(p[0])"
              :cy="sy(p[1])"
              r="3"
            >
              <title>{{ s.name }} @ {{ fmt(p[0]) }} = {{ fmt(p[1]) }}</title>
            </circle>
          </g>
        </g>

        <!-- axis captions -->
        <text v-if="block.x_label" class="chart__caption" :x="(W + PAD.l) / 2" :y="H - 6" text-anchor="middle">
          {{ block.x_label }}
        </text>
        <text
          v-if="block.y_label"
          class="chart__caption"
          :transform="`translate(13 ${(H - PAD.b + PAD.t) / 2}) rotate(-90)`"
          text-anchor="middle"
        >
          {{ block.y_label }}
        </text>
      </svg>
    </div>
  </figure>
</template>

<style scoped>
.chart {
  margin: 0;
}
.chart__title {
  font: 700 11px var(--mono);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ink-2);
  margin-bottom: 10px;
}
.chart__legend {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 8px;
}
.chart__key {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 11px;
  color: var(--ink-2);
}
.chart__swatch {
  width: 16px;
  height: 2px;
  background: var(--ink);
}
.chart__swatch.is-alt {
  background: var(--accent);
}
.chart__swatch[data-dashed='true'] {
  background: repeating-linear-gradient(90deg, currentColor 0 4px, transparent 4px 7px);
  color: var(--accent);
}

.chart__frame {
  border: 1px solid var(--rule-soft);
  background: var(--paper);
}
svg {
  display: block;
  width: 100%;
  height: auto;
}

.chart__grid line {
  stroke: var(--rule-soft);
  stroke-width: 1;
  stroke-dasharray: 2 4;
}
.chart__axis line {
  stroke: var(--ink-2);
  stroke-width: 1;
}
.chart__tick text {
  font: 10px var(--mono);
  fill: var(--ink-mute);
}
.chart__caption {
  font: 700 9px var(--mono);
  letter-spacing: 0.1em;
  fill: var(--ink-2);
}

.chart__line {
  fill: none;
  stroke: var(--ink);
  stroke-width: 1.75;
}
.is-alt .chart__line {
  stroke: var(--accent);
}
.chart__line.is-dashed {
  stroke-dasharray: 6 4;
  stroke-width: 1.25;
}
.chart__dot {
  fill: var(--paper);
  stroke: var(--ink);
  stroke-width: 1.5;
}
.is-alt .chart__dot {
  display: none;
}
.chart__bar {
  fill: var(--fill);
  opacity: 0.82;
}
.chart__bar:hover {
  opacity: 1;
}
.is-alt .chart__bar {
  fill: var(--accent);
}
</style>
