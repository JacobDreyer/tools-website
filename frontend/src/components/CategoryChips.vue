<script setup>
import { computed } from 'vue'
import { store } from '../store'

const props = defineProps({ modelValue: { type: String, default: '' } })
const emit = defineEmits(['update:modelValue'])

/* One chip row per level of the tree, revealed as you drill in. Depth is
   unbounded — a category can nest as deep as its children go. */
const levels = computed(() => {
  const rows = []
  const segments = props.modelValue.split('/').filter(Boolean)
  let nodes = store.categories
  let parentPath = ''

  for (let depth = 0; nodes.length; depth += 1) {
    const selected = segments[depth] || null
    rows.push({ depth, parentPath, nodes, selected })
    if (!selected) break
    const node = nodes.find((n) => n.id === selected)
    if (!node) break
    nodes = node.children
    parentPath = node.path
  }
  return rows
})

const total = computed(() => store.tools.length)
</script>

<template>
  <div class="chips">
    <div v-for="row in levels" :key="row.depth" class="chips__row">
      <span v-if="row.depth > 0" class="chips__branch">└</span>
      <button
        class="chip"
        :class="{ 'is-active': !row.selected, 'chip--sub': row.depth > 0 }"
        type="button"
        @click="emit('update:modelValue', row.parentPath)"
      >
        All<span v-if="row.depth === 0" class="chip__count">{{ total }}</span>
      </button>
      <button
        v-for="node in row.nodes"
        :key="node.path"
        class="chip"
        :class="{ 'is-active': row.selected === node.id, 'chip--sub': row.depth > 0 }"
        type="button"
        :title="node.description"
        @click="emit('update:modelValue', node.path)"
      >
        {{ node.name }}<span class="chip__count">{{ node.total }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.chips {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.chips__row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.chips__branch {
  color: var(--ink-2);
  font-size: 13px;
  margin-left: 6px;
  opacity: 0.7;
}
</style>
