/* Small dependency-free tokeniser. Good enough for reading a script on a
   drafting sheet; it is not a parser and does not try to be. */

const KEYWORDS = {
  py: `and as assert async await break class continue def del elif else except finally for from
       global if import in is lambda nonlocal not or pass raise return try while with yield
       None True False self`,
  js: `async await break case catch class const continue default delete do else export extends
       finally for from function if import in instanceof let new of return static super switch
       this throw try typeof var void while yield null true false undefined`,
  sh: `if then else elif fi for while do done case esac function return local export source echo
       exit set unset read`,
}
KEYWORDS.ts = KEYWORDS.js
KEYWORDS.go = `break case chan const continue default defer else fallthrough for func go goto if
  import interface map package range return select struct switch type var nil true false`
KEYWORDS.rs = `as break const continue crate else enum extern fn for if impl in let loop match mod
  move mut pub ref return self static struct trait true false type unsafe use where while`

const COMMENT = {
  py: /#[^\n]*/, sh: /#[^\n]*/,
  js: /\/\/[^\n]*|\/\*[\s\S]*?\*\//, ts: /\/\/[^\n]*|\/\*[\s\S]*?\*\//,
  go: /\/\/[^\n]*|\/\*[\s\S]*?\*\//, rs: /\/\/[^\n]*|\/\*[\s\S]*?\*\//,
}

const STRING = /"""[\s\S]*?"""|'''[\s\S]*?'''|`(?:\\.|[^`\\])*`|"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'/
const NUMBER = /\b\d[\d_]*\.?\d*(?:[eE][+-]?\d+)?\b/
const CALL = /\b[A-Za-z_]\w*(?=\s*\()/
const NAME = /\b[A-Za-z_]\w*\b/

const CACHE = new Map()

function patternFor(lang) {
  if (CACHE.has(lang)) return CACHE.get(lang)
  const comment = COMMENT[lang] || COMMENT.py
  const parts = [
    ['comment', comment],
    ['string', STRING],
    ['number', NUMBER],
    ['call', CALL],
    ['name', NAME],
  ]
  const re = new RegExp(parts.map(([, p]) => `(${p.source})`).join('|'), 'g')
  const entry = { re, kinds: parts.map(([k]) => k), words: wordSet(lang) }
  CACHE.set(lang, entry)
  return entry
}

function wordSet(lang) {
  return new Set((KEYWORDS[lang] || KEYWORDS.py).trim().split(/\s+/))
}

function escapeHtml(text) {
  return text.replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' })[c])
}

/** Returns HTML with <span class="tok-*"> wrappers. Input is escaped. */
export function highlight(code, lang = 'py') {
  const { re, kinds, words } = patternFor(lang)
  let out = ''
  let last = 0
  re.lastIndex = 0

  let match
  while ((match = re.exec(code)) !== null) {
    const text = match[0]
    if (!text) {
      re.lastIndex += 1
      continue
    }
    out += escapeHtml(code.slice(last, match.index))
    last = match.index + text.length

    let kind = kinds[match.slice(1).findIndex((g) => g !== undefined)]
    if (kind === 'name' || kind === 'call') {
      if (words.has(text)) kind = 'keyword'
      else if (kind === 'name') kind = null
    }
    out += kind ? `<span class="tok-${kind}">${escapeHtml(text)}</span>` : escapeHtml(text)
  }
  return out + escapeHtml(code.slice(last))
}
