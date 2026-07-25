<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import CategoryChips from '../components/CategoryChips.vue'
import ToolCard from '../components/ToolCard.vue'
import { categoryIndex, store } from '../store'

const route = useRoute()
const router = useRouter()

function queryBinding(key) {
  return computed({
    get: () => String(route.query[key] ?? ''),
    set: (value) => {
      const query = { ...route.query }
      if (value) query[key] = value
      else delete query[key]
      router.replace({ query })
    },
  })
}

const search = queryBinding('q')
const category = queryBinding('c')

const activeNode = computed(() => categoryIndex.value.get(category.value) || null)

const filtered = computed(() => {
  const needle = search.value.trim().toLowerCase()
  const path = category.value
  return store.tools.filter((tool) => {
    if (path && tool.category !== path && !tool.category.startsWith(`${path}/`)) return false
    if (!needle) return true
    return [tool.name, tool.summary, tool.description, tool.id, tool.category]
      .join(' ')
      .toLowerCase()
      .includes(needle)
  })
})
</script>

<template>
  <div>
    <div class="searchrow pad">
      <span class="searchrow__glyph">⊕</span>
      <input
        v-model="search"
        class="search-input"
        type="search"
        placeholder="Search schematic..."
        aria-label="Search tools"
      />
    </div>

    <div class="pad chipsrow">
      <CategoryChips v-model="category" />
      <p v-if="activeNode?.description" class="chipsrow__note micro">
        {{ activeNode.name }} — {{ activeNode.description }}
      </p>
    </div>

    <p v-if="store.errors.length" class="pad loaderr">
      ⚠ {{ store.errors.length }} tool module(s) failed to load:
      <span v-for="e in store.errors" :key="e.module" class="loaderr__item">
        {{ e.module }} — {{ e.error }}
      </span>
    </p>

    <div class="grid pad">
      <ToolCard v-for="tool in filtered" :key="tool.id" :tool="tool" />
    </div>

    <p v-if="store.loaded && !filtered.length" class="pad empty">
      — NO MATCHING ITEMS ON THIS SHEET —
    </p>
    <p v-if="!store.loaded && !store.error" class="pad empty">— READING INDEX —</p>
  </div>
</template>

<style scoped>
.searchrow {
  padding-top: 22px;
  display: flex;
  gap: 14px;
  align-items: center;
}
.searchrow__glyph {
  font-weight: 700;
  font-size: 12px;
  color: var(--ink-2);
}
.search-input {
  flex: 1;
  padding: 11px 14px;
}

.chipsrow {
  padding-top: 16px;
}
.chipsrow__note {
  margin: 10px 0 0;
  text-transform: none;
  letter-spacing: 0.02em;
  font-weight: 400;
  font-size: 12px;
  color: var(--ink-mute);
}

.grid {
  padding-top: 26px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  align-items: stretch;
}

.empty {
  text-align: center;
  color: var(--ink-mute);
  font-size: 12px;
  letter-spacing: 0.1em;
  padding-top: 40px;
}

.loaderr {
  margin-top: 20px;
  color: var(--accent);
  font-size: 12px;
  border: 1px dashed var(--accent);
  padding: 10px 14px;
}
.loaderr__item {
  display: block;
  opacity: 0.85;
}

@media (max-width: 1000px) {
  .grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 640px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
