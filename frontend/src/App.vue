<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { loadCatalog, store, toggleTheme, toolById } from './store'

const route = useRoute()

onMounted(() => loadCatalog())

const tool = computed(() =>
  route.name === 'tool' ? toolById(String(route.params.id)) : null,
)

const subtitle = computed(() => {
  if (tool.value) {
    return `DWG NO. ${tool.value.id.toUpperCase()} — ${tool.value.category
      .toUpperCase()
      .replace(/\//g, ' / ')} — SCALE 1:1`
  }
  return 'DWG NO. FK-04 — PERSONAL TOOLING — SCALE 1:1'
})

const stamp = computed(() => {
  if (tool.value) {
    return [
      'DRAWN BY: ME',
      `REV: ${tool.value.rev}`,
      `${tool.value.inputs.length} INPUTS`,
    ]
  }
  return ['DRAWN BY: ME', 'REV: C', `${store.tools.length} ITEMS`]
})

const footerLeft = computed(() =>
  tool.value ? `FIELD KIT — ${tool.value.name.toUpperCase()}` : 'FIELD KIT — TOOLING INDEX',
)
</script>

<template>
  <div class="sheet">
    <div class="sheet__grid" />
    <span class="mark mark--tl" />
    <span class="mark mark--tr" />
    <span class="mark mark--bl" />
    <span class="mark mark--br" />

    <header class="titleblock pad">
      <div>
        <RouterLink to="/" class="titleblock__title">Field Kit</RouterLink>
        <div class="titleblock__sub">{{ subtitle }}</div>
      </div>
      <div class="titleblock__right">
        <button class="btn btn--ghost" type="button" @click="toggleTheme">
          {{ store.theme === 'light' ? '◐ Negative' : '◑ Print' }}
        </button>
        <div class="stamp">
          <div v-for="line in stamp" :key="line">{{ line }}</div>
        </div>
      </div>
    </header>

    <div class="sheet__body">
      <p v-if="store.error" class="pad boot-error">
        ⚠ {{ store.error }}<br />
        <span class="micro">Start it with: py server/app.py</span>
      </p>
      <RouterView v-else />
    </div>

    <footer class="sheetfoot pad">
      <span>{{ footerLeft }}</span>
      <span>SHEET 1 OF 1</span>
    </footer>
  </div>
</template>

<style scoped>
.titleblock {
  padding-top: 34px;
  padding-bottom: 20px;
  border-bottom: 1px solid oklch(80% 0.05 245 / 0.5);
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 20px;
  flex-wrap: wrap;
}

.titleblock__title {
  font-size: 40px;
  font-weight: 700;
  letter-spacing: 0.01em;
  color: var(--ink);
  text-decoration: none;
  display: inline-block;
  line-height: 1.1;
}
.titleblock__title:hover {
  text-decoration: none;
  color: var(--accent);
}

.titleblock__sub {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: var(--ink-2);
  margin-top: 8px;
}

.titleblock__right {
  display: flex;
  align-items: flex-end;
  gap: 12px;
}

.stamp {
  text-align: right;
  font: 700 11px var(--mono);
  color: var(--ink-2);
  border: 1px solid var(--ink-2);
  padding: 8px 12px;
  white-space: nowrap;
  background: var(--paper);
}

.sheetfoot {
  border-top: 2px solid var(--ink-2);
  padding-top: 10px;
  padding-bottom: 10px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font: 700 10px var(--mono);
  letter-spacing: 0.08em;
  color: var(--ink-2);
}

.boot-error {
  margin: 40px 0;
  color: var(--accent);
  font-size: 13px;
}

@media (max-width: 700px) {
  .titleblock__title {
    font-size: 30px;
  }
  .titleblock__sub {
    font-size: 10px;
  }
}
</style>
