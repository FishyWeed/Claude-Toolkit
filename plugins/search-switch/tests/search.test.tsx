import { expect, test } from 'claude-code/testing'

const PROPS = { hasSurvey: false, isWorking: false, maxRows: 10, bodyColumns: 80, scroll: { offset: 0, bodyRows: 10 }, view: {} }

// Calls a tool the way a session does; the bottom hook stands for the tool running.
const call = ($: any, input: Record<string, unknown>) => $.tool.call({ tool_use_id: `t${Math.random()}`, ...input } as never) as Promise<any>

test('the dropdown switches mode, saves it, and the guard blocks the other side', async ($, on) => {
  const saved: Record<string, unknown> = {}
  on('store.get', ($, e) => ({ value: saved[e.key] }))
  on('store.set', ($, e) => {
    saved[e.key] = e.value
    return { value: undefined }
  })
  on('tool.call', () => ({ result: { text: 'ran' } }) as never)
  on('ui.render', ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    return <Box><Text>other-mod</Text></Box>
  })

  for (const surface of ['terminal', 'desktop'] as const) {
    const strip = await $.ui.mount({ plugin: 'search-switch', surface, component: 'AbovePrompt', props: PROPS })
    expect(await strip.find({ key: 'search-mode' })).toBeDefined()
    expect(await strip.find({ type: 'Text', text: 'other-mod' })).toBeDefined()
    await strip.unmount()
  }

  // Native (default): WebSearch runs, Exa and firecrawl are blocked.
  expect((await call($, { tool: 'WebSearch', query: 'x' })).deny).toBeUndefined()
  expect((await call($, { tool: 'mcp__plugin_exa_exa__web_search_exa', query: 'x' })).deny).toContain('Native')
  expect((await call($, { tool: 'Bash', command: 'firecrawl scrape "https://example.com"' })).deny).toContain('Native')
  expect((await call($, { tool: 'Bash', command: 'ls -la' })).deny).toBeUndefined()

  const strip = await $.ui.mount({ plugin: 'search-switch', surface: 'desktop', component: 'AbovePrompt', props: PROPS })
  await strip.select({ key: 'search-mode', value: 'exa' })
  expect(saved.mode).toBe('exa')

  // Exa / Firecrawl: native tools blocked, Exa and firecrawl run.
  expect((await call($, { tool: 'WebSearch', query: 'x' })).deny).toContain('Exa / Firecrawl')
  expect((await call($, { tool: 'WebFetch', url: 'https://example.com', prompt: 'x' })).deny).toContain('Exa / Firecrawl')
  expect((await call($, { tool: 'mcp__plugin_exa_exa__web_search_exa', query: 'x' })).deny).toBeUndefined()
  expect((await call($, { tool: 'Bash', command: 'firecrawl search "x"' })).deny).toBeUndefined()
})
