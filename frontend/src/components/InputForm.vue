<script setup>
import { computed, watch } from 'vue'

const props = defineProps({
  inputs: { type: Array, required: true },
  modelValue: { type: Object, required: true },
  badField: { type: String, default: null },
  badIndex: { type: Number, default: null },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'submit'])

/* ---- layout: fields fall into groups; list fields sharing a `table`
   key collapse into one grid with a row per index. ---------------------- */
const sections = computed(() => {
  const out = []
  let current = null
  for (const field of props.inputs) {
    const name = field.group || ''
    if (!current || current.name !== name) {
      current = { name, items: [] }
      out.push(current)
    }
    if (field.table) {
      const existing = current.items.find((i) => i.kind === 'table' && i.key === field.table)
      if (existing) existing.fields.push(field)
      else current.items.push({ kind: 'table', key: field.table, fields: [field] })
    } else {
      current.items.push({ kind: 'field', field })
    }
  }
  return out
})

function rowCount(fields) {
  return fields.reduce((n, f) => Math.max(n, (props.modelValue[f.id] || []).length), 0)
}

/* ---- writes -----------------------------------------------------------
   Written in place rather than by spreading into a fresh object: two edits
   landing in the same tick would each spread the same stale snapshot and the
   second would drop the first. The parent holds it in a ref, so mutating the
   proxy is what it observes anyway. */
function setValue(id, value) {
  props.modelValue[id] = value
  emit('update:modelValue', props.modelValue)
}

function setCell(id, index, value) {
  const list = [...(props.modelValue[id] || [])]
  list[index] = value
  setValue(id, list)
}

function fillDown(id) {
  const list = props.modelValue[id] || []
  if (!list.length) return
  setValue(id, list.map(() => list[0]))
}

/* ---- keep `length_from` vectors the size their driver says ------------- */
const drivers = computed(() => [
  ...new Set(props.inputs.filter((f) => f.length_from).map((f) => f.length_from)),
])

watch(
  () => drivers.value.map((id) => props.modelValue[id]),
  () => {
    for (const field of props.inputs) {
      if (!field.length_from) continue
      const target = Number(props.modelValue[field.length_from])
      if (!Number.isFinite(target) || target < 0 || target > 500) continue
      const list = [...(props.modelValue[field.id] || [])]
      if (list.length === target) continue
      while (list.length > target) list.pop()
      while (list.length < target) list.push(list.length ? list[list.length - 1] : 0)
      setValue(field.id, list)
    }
  },
)

function onKeydown(event) {
  if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') emit('submit')
}
</script>

<template>
  <form class="form" @submit.prevent="emit('submit')" @keydown="onKeydown">
    <fieldset v-for="(section, si) in sections" :key="si" class="section" :disabled="disabled">
      <legend v-if="section.name" class="section__legend">{{ section.name }}</legend>

      <template v-for="(item, ii) in section.items" :key="ii">
        <!-- scalar field -->
        <div v-if="item.kind === 'field'" class="fieldgrid">
          <label class="field" :class="{ 'field--wide': item.field.type === 'textarea' }">
            <span class="field__label">
              {{ item.field.label }}
              <em v-if="item.field.unit" class="field__unit">{{ item.field.unit }}</em>
            </span>

            <input
              v-if="['number', 'integer'].includes(item.field.type)"
              class="field-input"
              :class="{ 'is-bad': badField === item.field.id }"
              type="number"
              :step="item.field.step ?? (item.field.type === 'integer' ? 1 : 'any')"
              :min="item.field.min"
              :max="item.field.max"
              :value="modelValue[item.field.id]"
              @wheel.prevent
              @input="setValue(item.field.id, $event.target.value)"
            />

            <select
              v-else-if="item.field.type === 'select'"
              class="field-input"
              :class="{ 'is-bad': badField === item.field.id }"
              :value="modelValue[item.field.id]"
              @change="setValue(item.field.id, $event.target.value)"
            >
              <option v-for="opt in item.field.options" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>

            <textarea
              v-else-if="item.field.type === 'textarea'"
              class="field-input"
              :class="{ 'is-bad': badField === item.field.id }"
              :rows="item.field.rows || 6"
              :placeholder="item.field.placeholder"
              :value="modelValue[item.field.id]"
              @input="setValue(item.field.id, $event.target.value)"
            />

            <span v-else-if="item.field.type === 'boolean'" class="check">
              <input
                type="checkbox"
                :checked="!!modelValue[item.field.id]"
                @change="setValue(item.field.id, $event.target.checked)"
              />
              <span class="check__box">{{ modelValue[item.field.id] ? '×' : '' }}</span>
              <span class="check__text">{{ modelValue[item.field.id] ? 'YES' : 'NO' }}</span>
            </span>

            <input
              v-else
              class="field-input"
              :class="{ 'is-bad': badField === item.field.id }"
              type="text"
              :placeholder="item.field.placeholder"
              :value="modelValue[item.field.id]"
              @input="setValue(item.field.id, $event.target.value)"
            />

            <span v-if="item.field.help" class="field__help">{{ item.field.help }}</span>
          </label>
        </div>

        <!-- vector table -->
        <div v-else class="vtable-wrap">
          <table class="vtable">
            <thead>
              <tr>
                <th class="vtable__idx">#</th>
                <th v-for="f in item.fields" :key="f.id" :title="f.help || ''">
                  <div class="vtable__head">
                    <span>
                      {{ f.label }}
                      <em v-if="f.unit">{{ f.unit }}</em>
                    </span>
                    <button
                      class="btn btn--tiny"
                      type="button"
                      title="Copy the first value down the column"
                      @click="fillDown(f.id)"
                    >
                      ↓ fill
                    </button>
                  </div>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in rowCount(item.fields)" :key="r">
                <td class="vtable__idx">{{ r }}</td>
                <td v-for="f in item.fields" :key="f.id">
                  <input
                    class="field-input field-input--cell"
                    :class="{
                      'is-bad': badField === f.id && (badIndex === null || badIndex === r - 1),
                    }"
                    type="number"
                    step="any"
                    :value="(modelValue[f.id] || [])[r - 1]"
                    @wheel.prevent
                    @input="setCell(f.id, r - 1, $event.target.value)"
                  />
                </td>
              </tr>
            </tbody>
          </table>
          <p v-if="!rowCount(item.fields)" class="vtable__empty micro">— NO ROWS —</p>
        </div>
      </template>
    </fieldset>
  </form>
</template>

<style scoped>
.form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.section {
  border: none;
  border-top: 1px dotted var(--rule);
  margin: 0;
  padding: 14px 0 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.section:first-of-type {
  border-top: none;
  padding-top: 0;
}
.section__legend {
  font: 700 10px var(--mono);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ink-2);
  padding: 0 8px 0 0;
}

.fieldgrid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}
.field--wide {
  grid-column: 1 / -1;
}
.field__label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--ink-2);
}
.field__unit {
  font-style: normal;
  font-weight: 400;
  opacity: 0.75;
  text-transform: none;
  letter-spacing: 0;
}
.field__help {
  font-size: 11px;
  line-height: 1.45;
  color: var(--ink-mute);
}

.check {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  height: 41px;
}
.check input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}
.check__box {
  width: 20px;
  height: 20px;
  border: 1px solid var(--rule);
  display: grid;
  place-items: center;
  font-size: 15px;
  font-weight: 700;
  color: var(--ink);
  line-height: 1;
}
.check input:focus-visible + .check__box {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.check__text {
  font-size: 11px;
  letter-spacing: 0.08em;
  color: var(--ink-2);
}

/* vector table */
.vtable-wrap {
  overflow-x: auto;
  border: 1px solid var(--rule-soft);
}
.vtable {
  width: 100%;
  border-collapse: collapse;
}
.vtable th {
  padding: 7px 8px;
  border-bottom: 1px solid var(--ink-2);
  background: var(--paper-2);
  font: 700 10px var(--mono);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--ink-2);
  text-align: left;
  white-space: nowrap;
}
.vtable th em {
  font-style: normal;
  font-weight: 400;
  opacity: 0.75;
  text-transform: none;
}
.vtable__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.vtable td {
  padding: 0;
  border-bottom: 1px dotted var(--rule-soft);
}
.vtable tr:last-child td {
  border-bottom: none;
}
.vtable__idx {
  width: 42px;
  text-align: center !important;
  font-size: 11px;
  color: var(--ink-mute);
  background: var(--paper-2);
  border-right: 1px solid var(--rule-soft);
}
.field-input--cell {
  border: none;
  padding: 7px 9px;
  font-size: 13px;
  background: transparent;
  font-variant-numeric: tabular-nums;
}
.field-input--cell:focus {
  box-shadow: inset 0 0 0 1px var(--ink-2);
}
.vtable__empty {
  padding: 14px;
  text-align: center;
  color: var(--ink-mute);
}
</style>
