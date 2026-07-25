<script setup>
import { computed, ref } from 'vue'
import { highlight } from '../highlight'

const props = defineProps({
  code: { type: String, default: '' },
  lang: { type: String, default: 'py' },
  filename: { type: String, default: '' },
})

const wrapped = ref(false)
const copied = ref(false)

const lines = computed(() => props.code.replace(/\n$/, '').split('\n').length)
const html = computed(() => highlight(props.code.replace(/\n$/, ''), props.lang))

async function copy() {
  try {
    await navigator.clipboard.writeText(props.code)
  } catch {
    const area = document.createElement('textarea')
    area.value = props.code
    document.body.appendChild(area)
    area.select()
    document.execCommand('copy')
    area.remove()
  }
  copied.value = true
  setTimeout(() => (copied.value = false), 1600)
}
</script>

<template>
  <div class="code">
    <div class="code__bar">
      <span class="code__file">{{ filename || `source.${lang}` }}</span>
      <span class="code__meta">{{ lines }} LINES</span>
      <span class="code__spacer" />
      <button class="btn btn--tiny" type="button" @click="wrapped = !wrapped">
        {{ wrapped ? 'no wrap' : 'wrap' }}
      </button>
      <button class="btn btn--tiny" type="button" @click="copy">
        {{ copied ? '✓ copied' : 'copy' }}
      </button>
    </div>
    <pre class="code__body" :class="{ 'is-wrapped': wrapped }"><code v-html="html" /></pre>
  </div>
</template>

<style scoped>
.code {
  border: 1px solid var(--rule);
  background: var(--paper-2);
}
.code__bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 7px 10px;
  border-bottom: 1px solid var(--rule-soft);
  font: 700 10px var(--mono);
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--ink-2);
}
.code__spacer {
  flex: 1;
}
.code__meta {
  opacity: 0.65;
}

.code__body {
  margin: 0;
  padding: 14px 16px;
  overflow-x: auto;
  font: 12.5px/1.65 var(--mono);
  color: var(--ink-3);
  tab-size: 4;
  counter-reset: line;
}
.code__body.is-wrapped {
  white-space: pre-wrap;
  word-break: break-word;
}

.code__body :deep(.tok-comment) {
  color: var(--ink-mute);
  font-style: italic;
}
.code__body :deep(.tok-string) {
  color: var(--accent);
}
.code__body :deep(.tok-number) {
  color: var(--ok);
}
.code__body :deep(.tok-keyword) {
  color: var(--ink);
  font-weight: 700;
}
.code__body :deep(.tok-call) {
  color: var(--ink);
}
</style>
