import { expect, mock, test } from 'claude-code/testing'

const PANE = { component: 'Pane', props: { title: 'Swarm' }, requestId: 'swarm' } as const

test('a swarm specialist gets a live row: steps, elapsed time, then done', async ($, on) => {
  const clock = mock.clock(on, { now: 0 })
  mock.store(on)
  on('ui.open', () => ({ value: { isPlaced: true } }) as never)
  on('agent.spawn', () => ({ model: 'claude-sonnet-5-5', agentId: 'a1' }))
  on('tool.call', () => ({ result: 'ok' }) as never)
  on('turn.complete', () => ({ text: '' }))

  await $.agent.spawn({ prompt: 'Research meal kits', description: 'Research the meal-kit market', subagentType: 'swarm:researcher' } as never)
  // A non-swarm agent is not shown.
  await $.agent.spawn({ prompt: 'Look around', description: 'Explore the repo', subagentType: 'Explore' } as never)

  await $.tool.call({ tool: 'WebSearch', query: 'meal kit market size 2026', agentId: 'a1' } as never)
  await $.tool.call({ tool: 'Write', file_path: 'C:/out/research.md', content: '#', agentId: 'a1' } as never)
  await $.tool.call({ tool: 'Bash', command: 'ls', description: 'List files', agentId: 'other' } as never)
  await clock.advance(65_000)

  for (const surface of ['terminal', 'desktop', 'mobile'] as const) {
    const ui = await $.ui.mount({ plugin: 'swarm', surface, ...PANE } as never)
    expect(await ui.find({ type: 'Text', text: 'Research' })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: 'Research the meal-kit market' })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: 'Explore the repo' })).toBeUndefined()
    expect(await ui.find({ type: 'Text', text: /1m 05s · 2 steps/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: 'Write research.md' })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /1 running/ })).toBeDefined()
    await ui.unmount()
  }

  await $.turn.complete({ answer: 'Done', durationMs: 1, isAborted: false, turnId: 't1', agentId: 'a1', reason: 'answer' } as never)
  await clock.advance(30_000)

  const ui = await $.ui.mount({ plugin: 'swarm', surface: 'terminal', ...PANE } as never)
  expect(await ui.find({ type: 'Text', text: /1 done/ })).toBeDefined()
  // The clock stopped for the finished run.
  expect(await ui.find({ type: 'Text', text: /1m 05s · 2 steps/ })).toBeDefined()
  await ui.press({ key: 'clear' })
  expect(await ui.find({ type: 'Text', text: /No swarm agents yet/ })).toBeDefined()
  await ui.unmount()
})

test('a specialist whose loop errors is marked failed with the reason', async ($, on) => {
  mock.clock(on, { now: 0 })
  mock.store(on)
  on('ui.open', () => ({ value: { isPlaced: true } }) as never)
  on('agent.spawn', () => ({ model: 'm', agentId: 'b1' }))
  on('turn.complete', () => ({ text: '' }))

  await $.agent.spawn({ prompt: 'Make a deck', description: 'Build the pitch deck', subagentType: 'swarm:slides-designer' } as never)
  await $.turn.complete({ answer: '', durationMs: 1, isAborted: false, turnId: 't2', agentId: 'b1', reason: 'error' } as never)

  const ui = await $.ui.mount({ plugin: 'swarm', surface: 'terminal', ...PANE } as never)
  expect(await ui.find({ type: 'Text', text: 'Slides' })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /1 failed/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: 'error' })).toBeDefined()
  await ui.unmount()
})
