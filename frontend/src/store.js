import { computed, reactive, readonly } from 'vue'
import { api } from './api'

const state = reactive({
  categories: [],
  tools: [],
  errors: [],
  loaded: false,
  loading: false,
  error: null,
  theme: localStorage.getItem('fk.theme') || 'light',
})

applyTheme(state.theme)

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme)
}

export function toggleTheme() {
  state.theme = state.theme === 'light' ? 'dark' : 'light'
  localStorage.setItem('fk.theme', state.theme)
  applyTheme(state.theme)
}

export async function loadCatalog(force = false) {
  if (state.loading || (state.loaded && !force)) return
  state.loading = true
  state.error = null
  try {
    const data = await api.catalog()
    state.categories = data.categories
    state.tools = data.tools
    state.errors = data.errors || []
    state.loaded = true
  } catch (err) {
    state.error = err.message
  } finally {
    state.loading = false
  }
}

/** Flat map of "slug/path" -> category node, for breadcrumbs and labels. */
export const categoryIndex = computed(() => {
  const index = new Map()
  const walk = (nodes) => {
    for (const node of nodes) {
      index.set(node.path, node)
      walk(node.children)
    }
  }
  walk(state.categories)
  return index
})

/** ["Electrical", "Power Distribution"] for a slug path. */
export function categoryTrail(path) {
  const index = categoryIndex.value
  const out = []
  let walked = ''
  for (const slug of (path || '').split('/').filter(Boolean)) {
    walked = walked ? `${walked}/${slug}` : slug
    const node = index.get(walked)
    out.push({ path: walked, name: node ? node.name : slug })
  }
  return out
}

export function toolById(id) {
  return state.tools.find((t) => t.id === id)
}

export const store = readonly(state)
