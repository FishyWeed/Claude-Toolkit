import { describe, expect, test } from 'claude-code/testing'

import { classify } from '../hooks/classify'

const PROPS = { hasSurvey: false, isWorking: false, maxRows: 10, bodyColumns: 80, scroll: { offset: 0, bodyRows: 10 }, view: {} }

describe('classify', () => {
  test('sorts prompts into tiers', async () => {
    expect(classify('fix the typo in README')?.model).toBe('haiku')
    expect(classify('write a commit message for these changes')?.model).toBe('haiku')
    expect(classify('add a logout button to the navbar component')?.model).toBe('sonnet')
    expect(classify('debug why the checkout test is failing')?.model).toBe('opus')
    expect(classify('refactor the auth module and migrate to the new API')?.model).toBe('opus')
    expect(classify('research the best budget running shoes')?.model).toBe('opus')
    expect(classify('thanks!')).toBeNull()
  })
})

// Launches a subagent the way a session does; the bottom hook records what reached it.
const spawn = ($: any, input: Record<string, unknown>) =>
  $.tool.call({ tool: 'Agent', tool_use_id: `t${Math.random()}`, description: 'task', prompt: 'do it', ...input } as never) as Promise<any>

test('every subagent gets a model, swarm specialists by type, explicit choices win, Off turns it off', async ($, on) => {
  const saved: Record<string, unknown> = {}
  on('store.get', ($, e) => ({ value: saved[e.key] }))
  on('store.set', ($, e) => {
    saved[e.key] = e.value
    return { value: undefined }
  })
  const launched: Array<string | undefined> = []
  on('tool.call', ($, e) => {
    launched.push((e as { model?: string }).model)
    return { result: { text: 'done' } } as never
  })
  on('ui.render', ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    return <Box><Text>other-mod</Text></Box>
  })

  await spawn($, { subagent_type: 'swarm:researcher' })
  await spawn($, { subagent_type: 'swarm:image-maker' })
  await spawn($, { subagent_type: 'general-purpose', description: 'debug flaky test', prompt: 'find the root cause of the flaky login test' })
  await spawn($, { subagent_type: 'general-purpose', description: 'rename files', prompt: 'rename the files' })
  await spawn($, { subagent_type: 'swarm:researcher', model: 'opus' })
  await spawn($, { subagent_type: 'fork' })
  expect(launched).toEqual(['sonnet', 'haiku', 'opus', 'haiku', 'opus', undefined])

  for (const surface of ['terminal', 'desktop'] as const) {
    const strip = await $.ui.mount({ plugin: 'model-router', surface, component: 'AbovePrompt', props: PROPS })
    expect(await strip.find({ key: 'router' })).toBeDefined()
    expect(await strip.find({ type: 'Text', text: 'other-mod' })).toBeDefined()
    await strip.unmount()
  }

  const strip = await $.ui.mount({ plugin: 'model-router', surface: 'desktop', component: 'AbovePrompt', props: PROPS })
  await strip.select({ key: 'router', value: 'off' })
  expect(saved.enabled).toBe(false)
  await spawn($, { subagent_type: 'swarm:researcher' })
  expect(launched.at(-1)).toBeUndefined()
})
