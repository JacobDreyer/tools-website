<script setup>
import { computed } from 'vue'

const props = defineProps({ tool: { type: Object, required: true } })

const ref_ = computed(() => {
  const leaf = props.tool.category.split('/').filter(Boolean).pop() || 'misc'
  return leaf.toUpperCase()
})
</script>

<template>
  <RouterLink class="card" :to="{ name: 'tool', params: { id: tool.id } }">
    <span class="card__tick" />
    <div class="card__name">{{ tool.name }}</div>
    <div class="card__desc">{{ tool.summary }}</div>
    <div class="card__foot">
      <span>REF/{{ ref_ }}</span>
      <span>{{ tool.tag }}</span>
    </div>
  </RouterLink>
</template>

<style scoped>
.card {
  border: 1px solid var(--rule);
  padding: 16px;
  position: relative;
  display: flex;
  flex-direction: column;
  color: inherit;
  text-decoration: none;
  background: transparent;
  transition: background 0.12s linear, border-color 0.12s linear;
}
.card:hover {
  text-decoration: none;
  border-color: var(--ink-2);
  background: var(--hover);
}
.card:hover .card__tick {
  width: 34px;
}
.card:hover .card__name {
  color: var(--accent);
}

.card__tick {
  position: absolute;
  top: -1px;
  left: 14px;
  width: 10px;
  height: 2px;
  background: var(--ink-2);
  transition: width 0.12s linear;
}

.card__name {
  font-size: 15px;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--ink);
  line-height: 1.35;
}

.card__desc {
  font-size: 13px;
  color: var(--ink-3);
  margin-top: 8px;
  line-height: 1.5;
  flex: 1;
}

.card__foot {
  margin-top: 14px;
  padding-top: 8px;
  border-top: 1px dotted var(--ink-mute);
  font-size: 11px;
  letter-spacing: 0.04em;
  color: var(--ink-2);
  display: flex;
  justify-content: space-between;
  gap: 8px;
}
</style>
