<script setup>
import ChartBlock from './blocks/ChartBlock.vue'

defineProps({ blocks: { type: Array, required: true } })

const NOTICE_GLYPH = { info: '⊕', ok: '✓', warn: '⚠', error: '✕' }

function cell(value) {
  return value !== null && typeof value === 'object' ? value : { value, flag: false }
}
</script>

<template>
  <div class="result">
    <template v-for="(block, i) in blocks" :key="i">
      <!-- metric strip -->
      <div v-if="block.type === 'metrics'" class="metrics">
        <div
          v-for="item in block.items"
          :key="item.label"
          class="metric"
          :class="{ 'is-emphasis': item.emphasis }"
        >
          <div class="metric__label">{{ item.label }}</div>
          <div class="metric__value">
            {{ item.value }}<em v-if="item.unit" class="metric__unit">{{ item.unit }}</em>
          </div>
          <div v-if="item.hint" class="metric__hint">{{ item.hint }}</div>
        </div>
      </div>

      <!-- notice -->
      <p v-else-if="block.type === 'notice'" class="notice" :class="`is-${block.level}`">
        <span class="notice__glyph">{{ NOTICE_GLYPH[block.level] || '⊕' }}</span>
        <span>{{ block.body }}</span>
      </p>

      <!-- table -->
      <div v-else-if="block.type === 'table'" class="unit">
        <div v-if="block.title" class="unit__title">{{ block.title }}</div>
        <div class="dtable-wrap">
          <table class="dtable">
            <thead>
              <tr>
                <th
                  v-for="(col, ci) in block.columns"
                  :key="ci"
                  :class="{ al: col.align === 'left' }"
                >
                  {{ col.label }}<span v-if="col.unit" class="u">{{ col.unit }}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, ri) in block.rows" :key="ri">
                <td
                  v-for="(raw, ci) in row"
                  :key="ci"
                  :class="{
                    al: block.columns[ci]?.align === 'left',
                    'is-flagged': cell(raw).flag,
                  }"
                >
                  {{ cell(raw).value }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="block.note" class="unit__note">{{ block.note }}</p>
      </div>

      <!-- chart -->
      <ChartBlock v-else-if="block.type === 'chart'" :block="block" />

      <!-- prose -->
      <div v-else-if="block.type === 'text'" class="unit">
        <div v-if="block.title" class="unit__title">{{ block.title }}</div>
        <p class="prose">{{ block.body }}</p>
      </div>

      <!-- raw log / json -->
      <div v-else class="unit">
        <div v-if="block.title" class="unit__title">{{ block.title }}</div>
        <pre class="raw">{{
          block.type === 'json' ? JSON.stringify(block.data, null, 2) : block.body
        }}</pre>
      </div>
    </template>
  </div>
</template>

<style scoped>
.result {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

/* metrics ---------------------------------------------------------- */
.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(158px, 1fr));
  gap: 1px;
  background: var(--rule-soft);
  border: 1px solid var(--rule-soft);
}
.metric {
  background: var(--paper);
  padding: 12px 14px;
  border-top: 2px solid transparent;
}
.metric.is-emphasis {
  border-top-color: var(--ink-2);
  background: var(--paper-2);
}
.metric__label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--ink-2);
}
.metric__value {
  font-size: 21px;
  font-weight: 700;
  color: var(--ink);
  margin-top: 3px;
  line-height: 1.25;
  font-variant-numeric: tabular-nums;
  word-break: break-word;
}
.metric__unit {
  font-style: normal;
  font-size: 12px;
  font-weight: 400;
  color: var(--ink-2);
  margin-left: 4px;
}
.metric__hint {
  font-size: 11px;
  color: var(--ink-mute);
  margin-top: 4px;
  line-height: 1.4;
}

/* notice ----------------------------------------------------------- */
.notice {
  margin: 0;
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 11px 14px;
  font-size: 12.5px;
  line-height: 1.55;
  border: 1px solid var(--rule);
  color: var(--ink-3);
}
.notice__glyph {
  font-weight: 700;
}
.notice.is-warn,
.notice.is-error {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--accent);
}
.notice.is-ok {
  border-color: var(--ok);
  background: var(--ok-soft);
  color: var(--ok);
}

/* generic unit ----------------------------------------------------- */
.unit__title {
  font: 700 11px var(--mono);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ink-2);
  margin-bottom: 10px;
}
.unit__note {
  margin: 9px 0 0;
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--ink-mute);
  max-width: 80ch;
}

.raw {
  margin: 0;
  padding: 12px 14px;
  border: 1px solid var(--rule-soft);
  background: var(--paper-2);
  font: 12px/1.6 var(--mono);
  color: var(--ink-3);
  overflow-x: auto;
  white-space: pre;
}
</style>
