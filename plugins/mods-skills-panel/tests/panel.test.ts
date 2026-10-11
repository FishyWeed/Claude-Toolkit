import { expect, mock, test } from 'claude-code/testing'

const PANE = { component: 'Pane', props: { title: 'Mods & Skills' }, requestId: 'mods-skills' } as const

test('rows are numbered names that expand on click; the toggle switches lists and the model button cycles', async ($, on) => {
  mock.clock(on, { now: 0 })
  mock.store(on)
  mock.env(on, { HOME: '/home/test' })
  on('fs.exists', () => ({ value: false }) as never)
  on('ui.open', () => ({ value: { isPlaced: true } }) as never)
  on('command.list', () =>
    ({
      value: [
        { name: 'demo', description: 'Runs the demo.', source: 'plugin', plugin: 'demo-mod' },
        { name: 'pdf', description: 'Work with PDF files.', source: 'user' },
      ],
    }) as never,
  )
  on('session.usage', () =>
    ({
      value: {
        startedAt: 0,
        rateLimits: [],
        context: { breakdown: { skills: { skillFrontmatter: [{ name: 'pdf', source: 'built-in', tokens: 10 }] } } },
      },
    }) as never,
  )

  await $.command.run({ command: 'mods-skills', args: '' })

  for (const surface of ['desktop', 'mobile', 'terminal'] as const) {
    const ui = await $.ui.mount({ plugin: 'mods-skills-panel', surface, ...PANE })

    if (!(await ui.find({ type: 'Text', text: 'demo-mod' }))) await ui.press({ key: 'tab-mods' })
    // Collapsed: a numbered name only.
    expect(await ui.find({ type: 'Text', text: 'demo-mod' })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /^1\.\s*$/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: 'Commands: /demo' })).toBeUndefined()
    expect(await ui.find({ key: 'model-mod:demo-mod' })).toBeUndefined()

    // A click opens the details.
    await ui.press({ key: 'row-mod:demo-mod' })
    expect(await ui.find({ type: 'Text', text: 'Commands: /demo' })).toBeDefined()
    expect((await ui.find({ type: 'Text', text: '● loaded' }))?.props.color).toBe('suggestion')

    const before = (await ui.find({ key: 'model-mod:demo-mod' }))?.text
    await ui.press({ key: 'model-mod:demo-mod' })
    expect((await ui.find({ key: 'model-mod:demo-mod' }))?.text).not.toBe(before)

    // A second click closes them again.
    await ui.press({ key: 'row-mod:demo-mod' })
    expect(await ui.find({ type: 'Text', text: 'Commands: /demo' })).toBeUndefined()

    await ui.press({ key: 'tab-skills' })
    expect(await ui.find({ type: 'Text', text: 'pdf' })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: 'Work with PDF files.' })).toBeUndefined()
    expect(await ui.find({ type: 'Text', text: 'demo-mod' })).toBeUndefined()
    await ui.press({ key: 'row-skill:pdf' })
    expect(await ui.find({ type: 'Text', text: 'Work with PDF files.' })).toBeDefined()
    expect((await ui.find({ type: 'Text', text: '● built-in' }))?.props.color).toBe('suggestion')
    // Collapse all closes every open row.
    await ui.press({ key: 'collapse-all' })
    expect(await ui.find({ type: 'Text', text: 'Work with PDF files.' })).toBeUndefined()
    await ui.press({ key: 'tab-mods' })

    await ui.unmount()
  }
})

test('a skill with an assigned model runs its turn on that model', async ($, on) => {
  mock.clock(on, { now: 0 })
  mock.store(on, { models: { 'skill:pdf': 'haiku' } })
  on('ui.open', () => ({ value: { isPlaced: true } }) as never)
  on('command.register', e => ({ value: { command: e.name } }) as never)
  on('fs.exists', () => ({ value: false }) as never)
  on('command.list', () => ({ value: [] }) as never)
  on('session.usage', () => ({ value: { startedAt: 0, rateLimits: [], context: {} } }) as never)
  on('session.start', () => ({ cwd: '/tmp' }) as never)
  on('skill.prompt', () => ({ text: 'Use the PDF skill.' }))

  let sentModel = ''
  on('turn.step', async function* (_$, e) {
    sentModel = e.model
    return { turnId: e.turnId, index: e.index, answer: '', toolUses: [], stopReason: 'end_turn' } as never
  })

  await $.session.start({ source: 'startup', cwd: '/tmp' } as never)
  await $.skill.prompt({ skill: 'pdf', text: 'Use the PDF skill.' })
  const stream = $.turn.step({ turnId: 't1', index: 0, model: 'claude-opus-5-5', messageCount: 1 })
  for await (const _ of stream) void _
  expect(sentModel).toBe('haiku')
})
