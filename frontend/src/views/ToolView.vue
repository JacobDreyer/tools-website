<script setup>
import { computed, ref, watch } from 'vue'
import CodeBlock from '../components/CodeBlock.vue'
import InputForm from '../components/InputForm.vue'
import ResultView from '../components/ResultView.vue'
import { api } from '../api'
import { categoryTrail } from '../store'

const props = defineProps({ id: { type: String, required: true } })

const tool = ref(null)
const params = ref({})
const result = ref(null)
const stdout = ref('')
const elapsed = ref(null)
const error = ref(null)
const badField = ref(null)
const badIndex = ref(null)
const running = ref(false)
const loadError = ref(null)

const trail = computed(() => (tool.value ? categoryTrail(tool.value.category) : []))
const storageKey = computed(() => `fk.params.${props.id}`)

function defaults(spec) {
  const out = {}
  for (const field of spec.inputs) {
    out[field.id] = Array.isArray(field.default) ? [...field.default] : field.default
  }
  return out
}

function restore(spec) {
  const base = defaults(spec)
  try {
    const saved = JSON.parse(localStorage.getItem(`fk.params.${spec.id}`) || 'null')
    if (saved && typeof saved === 'object') {
      for (const field of spec.inputs) {
        if (field.id in saved) base[field.id] = saved[field.id]
      }
    }
  } catch {
    /* a corrupt entry just means we fall back to defaults */
  }
  return base
}

watch(
  () => props.id,
  async (id) => {
    tool.value = null
    result.value = null
    error.value = null
    loadError.value = null
    elapsed.value = null
    try {
      const spec = await api.tool(id)
      tool.value = spec
      params.value = restore(spec)
      if (spec.autorun) run()
    } catch (err) {
      loadError.value = err.message
    }
  },
  { immediate: true },
)

watch(
  params,
  (value) => {
    if (tool.value) localStorage.setItem(storageKey.value, JSON.stringify(value))
  },
  { deep: true },
)

async function run() {
  if (running.value) return
  running.value = true
  error.value = null
  badField.value = null
  badIndex.value = null
  try {
    const response = await api.run(props.id, params.value)
    if (response.ok) {
      result.value = response.result
      stdout.value = response.stdout || ''
      elapsed.value = response.elapsed_ms
    } else {
      error.value = response
      badField.value = response.field || null
      badIndex.value = response.index ?? null
    }
  } catch (err) {
    error.value = { error: err.message, kind: 'network' }
  } finally {
    running.value = false
  }
}

function reset() {
  if (!tool.value) return
  params.value = defaults(tool.value)
  localStorage.removeItem(storageKey.value)
}
</script>

<template>
  <div class="pad tool">
    <p v-if="loadError" class="tool__loaderr">⚠ {{ loadError }}</p>
    <p v-else-if="!tool" class="tool__loading micro">— OPENING SHEET —</p>

    <template v-else>
      <nav class="crumbs">
        <RouterLink to="/">INDEX</RouterLink>
        <template v-for="node in trail" :key="node.path">
          <span class="crumbs__sep">/</span>
          <RouterLink :to="{ path: '/', query: { c: node.path } }">
            {{ node.name.toUpperCase() }}
          </RouterLink>
        </template>
      </nav>

      <h1 class="tool__name">{{ tool.name }}</h1>
      <p class="tool__summary">{{ tool.summary }}</p>
      <p v-if="tool.description" class="prose tool__desc">{{ tool.description }}</p>

      <div class="split">
        <!-- inputs ------------------------------------------------ -->
        <section class="panel">
          <div class="panel__head">
            <span>Inputs</span>
            <span class="panel__meta">{{ tool.inputs.length }} params</span>
          </div>
          <div class="panel__body">
            <InputForm
              v-model="params"
              :inputs="tool.inputs"
              :bad-field="badField"
              :bad-index="badIndex"
              :disabled="running"
              @submit="run"
            />
            <div class="runbar">
              <button class="btn btn--primary" type="button" :disabled="running" @click="run">
                {{ running ? 'Running…' : '▶ Run' }}
              </button>
              <button class="btn" type="button" :disabled="running" @click="reset">Reset</button>
              <span class="runbar__hint micro">ctrl + enter</span>
            </div>

            <ul v-if="tool.notes.length" class="notes">
              <li v-for="note in tool.notes" :key="note">{{ note }}</li>
            </ul>
          </div>
        </section>

        <!-- output ------------------------------------------------ -->
        <section class="panel">
          <div class="panel__head">
            <span>Output</span>
            <span class="panel__meta">
              <template v-if="running">solving…</template>
              <template v-else-if="error">fault</template>
              <template v-else-if="elapsed !== null">{{ elapsed }} ms</template>
              <template v-else>idle</template>
            </span>
          </div>
          <div class="panel__body">
            <div v-if="error" class="fault">
              <div class="fault__head">
                {{
                  { input: 'Input rejected', timeout: 'Timed out', tool: 'Cannot solve',
                    crash: 'Unhandled exception', network: 'No server' }[error.kind] || 'Fault'
                }}
              </div>
              <p class="fault__msg">{{ error.error }}</p>
              <p v-if="error.detail && error.kind !== 'crash'" class="fault__detail">
                {{ error.detail }}
              </p>
              <pre v-else-if="error.detail" class="fault__trace">{{ error.detail }}</pre>
            </div>

            <ResultView v-if="result && !error" :blocks="result.blocks" />

            <div v-if="stdout && !error" class="stdout">
              <div class="unit__title">Console</div>
              <pre class="raw">{{ stdout }}</pre>
            </div>

            <p v-if="!result && !error && !running" class="idle micro">
              — RUN TO POPULATE THIS PANEL —
            </p>
          </div>
        </section>
      </div>

      <!-- source ---------------------------------------------------- -->
      <section class="panel panel--source">
        <div class="panel__head">
          <span>Source</span>
          <span class="panel__meta">{{ tool.source_file }}</span>
        </div>
        <div class="panel__body">
          <CodeBlock :code="tool.source" :lang="tool.tag" :filename="tool.source_file" />
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.tool {
  padding-top: 24px;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.crumbs {
  font: 700 10px var(--mono);
  letter-spacing: 0.1em;
  color: var(--ink-2);
  display: flex;
  gap: 7px;
  flex-wrap: wrap;
}
.crumbs a {
  color: var(--ink-2);
}
.crumbs a:hover {
  color: var(--accent);
}
.crumbs__sep {
  opacity: 0.5;
}

.tool__name {
  font-size: 26px;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--ink);
  margin: 12px 0 0;
  line-height: 1.25;
}
.tool__summary {
  margin: 8px 0 0;
  font-size: 14px;
  color: var(--ink-3);
  max-width: 88ch;
}
.tool__desc {
  margin: 14px 0 0;
  padding-left: 14px;
  border-left: 1px dotted var(--rule);
  font-size: 13px;
  color: var(--ink-mute);
}

.split {
  margin-top: 26px;
  display: grid;
  grid-template-columns: minmax(320px, 5fr) minmax(0, 7fr);
  gap: 18px;
  align-items: start;
}

.panel__meta {
  font-weight: 400;
  opacity: 0.7;
  letter-spacing: 0.04em;
  text-transform: none;
}
.panel--source {
  margin-top: 18px;
}

.runbar {
  margin-top: 20px;
  padding-top: 14px;
  border-top: 1px dotted var(--rule);
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.runbar__hint {
  color: var(--ink-mute);
  opacity: 0.8;
  font-weight: 400;
}

.notes {
  margin: 16px 0 0;
  padding: 0;
  list-style: none;
  font-size: 11.5px;
  color: var(--ink-mute);
  line-height: 1.55;
}
.notes li {
  padding-left: 14px;
  position: relative;
}
.notes li::before {
  content: '—';
  position: absolute;
  left: 0;
  opacity: 0.6;
}

.fault {
  border: 1px solid var(--accent);
  background: var(--accent-soft);
  padding: 12px 14px;
  color: var(--accent);
}
.fault__head {
  font: 700 10px var(--mono);
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.fault__msg {
  margin: 7px 0 0;
  font-size: 13px;
  line-height: 1.5;
}
.fault__detail {
  margin: 8px 0 0;
  font-size: 11.5px;
  line-height: 1.5;
  opacity: 0.85;
}
.fault__trace {
  margin: 10px 0 0;
  font-size: 11px;
  line-height: 1.5;
  overflow-x: auto;
  max-height: 260px;
  opacity: 0.85;
}

.stdout {
  margin-top: 22px;
}
.unit__title {
  font: 700 11px var(--mono);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ink-2);
  margin-bottom: 10px;
}
.raw {
  margin: 0;
  padding: 12px 14px;
  border: 1px solid var(--rule-soft);
  background: var(--paper-2);
  font: 12px/1.6 var(--mono);
  color: var(--ink-3);
  overflow-x: auto;
  max-height: 320px;
}

.idle,
.tool__loading {
  text-align: center;
  color: var(--ink-mute);
  padding: 40px 0;
  letter-spacing: 0.1em;
}
.tool__loaderr {
  color: var(--accent);
  padding: 40px 0;
}

@media (max-width: 1000px) {
  .split {
    grid-template-columns: 1fr;
  }
}
</style>
