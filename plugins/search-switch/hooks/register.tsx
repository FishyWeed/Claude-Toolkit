import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { SearchMode } from '../types'

const mode = atom({ plugin: 'search-switch', key: 'mode' } as const, 'native' as SearchMode)

const OPTIONS = [
  { value: 'native', label: 'Native' },
  { value: 'exa', label: 'Exa / Firecrawl' },
]

const NATIVE_TOOLS = new Set(['WebSearch', 'WebFetch'])
// Exa's MCP tools, whether it is installed as a plugin or as a plain MCP server.
const isExaTool = (tool: string) => tool.startsWith('mcp__plugin_exa_') || tool.startsWith('mcp__exa__')
const isFirecrawlCommand = (command: unknown) =>
  typeof command === 'string' && /^\s*(npx\s+(-y\s+)?)?firecrawl(-cli)?\b/.test(command)

const GUIDE: Record<SearchMode, string> = {
  native:
    'Web search mode: Native. For web search and fetching pages, use the built-in WebSearch and WebFetch tools. ' +
    'Do not use the Exa MCP tools or the firecrawl CLI; they are blocked in this mode.',
  exa:
    'Web search mode: Exa / Firecrawl. Do not use the built-in WebSearch or WebFetch tools; they are blocked in this mode. ' +
    'For web search, use the Exa MCP tools (web_search_exa, and web_fetch_exa to read a page). ' +
    'For scraping, crawling or mapping a site, or when a page needs JavaScript rendering, use the firecrawl CLI through the Firecrawl skills. ' +
    'If a tool fails because it is not signed in or is rate-limited, tell the user instead of falling back to WebSearch or WebFetch.',
}

const setMode = async ($: EngineInterface, next: SearchMode) => {
  await update($, mode, () => next)
  await $.store.set('mode', next)
}

const parseMode = (raw: string): SearchMode | undefined => {
  const v = raw.trim().toLowerCase()
  if (v === 'native') return 'native'
  if (v === 'exa' || v === 'firecrawl' || v === 'exa/firecrawl') return 'exa'
  return undefined
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const saved = await $.store.get('mode').catch(() => undefined)
    if (saved === 'native' || saved === 'exa') await update($, mode, () => saved)
    await $.command.register({ name: 'search', description: 'Show or set the web search mode: native or exa' })
    return next(e)
  })

  on('command.run', { command: 'search' }, async ($, e) => {
    if (!e.args.trim()) return { text: `Search mode: ${(await read($, mode)) === 'exa' ? 'Exa / Firecrawl' : 'Native'}` }
    const picked = parseMode(e.args)
    if (!picked) return { text: 'Use /search native or /search exa' }
    await setMode($, picked)
    return { text: `Search mode set to ${picked === 'exa' ? 'Exa / Firecrawl' : 'Native'}` }
  })

  // Tell Claude which search tools to use.
  on('prompt.compose', async ($, e, next) => {
    const composed = await next(e)
    const current = await read($, mode)
    return { sections: [...composed.sections, { id: 'search-switch:mode', text: GUIDE[current], scope: 'session' as const }] }
  })

  // Block the other side's tools so the choice holds.
  on('tool.call', async ($, e, next) => {
    const current = await read($, mode)
    if (current === 'exa' && NATIVE_TOOLS.has(e.tool)) {
      return { deny: `Search mode is Exa / Firecrawl, so ${e.tool} is blocked. Use the Exa MCP tools or the firecrawl CLI.` }
    }
    if (current === 'native' && isExaTool(e.tool)) {
      return { deny: 'Search mode is Native, so Exa tools are blocked. Use WebSearch or WebFetch.' }
    }
    if (current === 'native' && e.tool === 'Bash' && isFirecrawlCommand((e as { command?: unknown }).command)) {
      return { deny: 'Search mode is Native, so the firecrawl CLI is blocked. Use WebSearch or WebFetch.' }
    }
    return next(e)
  }).catch(($, e, next) => next(e))

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const rest = await next(e)
    if (e.props.hasSurvey) return rest

    const { Box, Select, Text } = $.ui.resolve(e)
    const current = await read($, mode)

    return (
      <Box>
        <Select key="search-mode" label="Search" options={OPTIONS} value={current} onSelect={v => setMode($, v === 'exa' ? 'exa' : 'native')} />
        <Text>  </Text>
        {rest}
      </Box>
    )
  })
}
