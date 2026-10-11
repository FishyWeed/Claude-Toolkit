import { expect, mock, test } from 'claude-code/testing'

const PROPS = { hasSurvey: false, isWorking: false, maxRows: 10, bodyColumns: 80, scroll: { offset: 0, bodyRows: 10 }, view: {} }

test('Skills and Mods buttons above the prompt open the panel on that list', async ($, on) => {
  mock.clock(on, { now: 0 })
  mock.store(on)
  mock.env(on, { HOME: '/home/test' })
  const opened: string[] = []
  on('fs.exists', () => ({ value: false }) as never)
  on('ui.open', ($, e) => {
    opened.push(e.id)
    return { value: { isPlaced: true } } as never
  })
  on('command.list', () => ({ value: [{ name: 'demo', description: 'Runs the demo.', source: 'plugin', plugin: 'demo-mod' }] }) as never)
  on('session.usage', () => ({ value: { startedAt: 0, rateLimits: [], context: { breakdown: { skills: { skillFrontmatter: [{ name: 'pdf', source: 'built-in', tokens: 10 }] } } } } }) as never)
  // Stands in for what other mods draw in the same strip.
  on('ui.render', ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    return <Box><Text>other-mod</Text></Box>
  })

  for (const surface of ['terminal', 'desktop'] as const) {
    const strip = await $.ui.mount({ plugin: 'mods-skills-panel', surface, component: 'AbovePrompt', props: PROPS })
    expect(await strip.find({ key: 'show-skills' })).toBeDefined()
    expect(await strip.find({ key: 'show-mods' })).toBeDefined()
    expect(await strip.find({ type: 'Text', text: 'other-mod' })).toBeDefined()

    await strip.press({ key: 'show-skills' })
    expect(opened.at(-1)).toBe('mods-skills')
    const pane = await $.ui.mount({ plugin: 'mods-skills-panel', surface, component: 'Pane', props: { title: 'Mods & Skills' }, requestId: 'mods-skills' })
    expect(await pane.find({ type: 'Text', text: 'pdf' })).toBeDefined()
    await pane.unmount()

    await strip.press({ key: 'show-mods' })
    const pane2 = await $.ui.mount({ plugin: 'mods-skills-panel', surface, component: 'Pane', props: { title: 'Mods & Skills' }, requestId: 'mods-skills' })
    expect(await pane2.find({ type: 'Text', text: 'demo-mod' })).toBeDefined()
    await pane2.unmount()
    await strip.unmount()
  }

  // A survey keeps the strip to itself.
  const busy = await $.ui.mount({ plugin: 'mods-skills-panel', surface: 'terminal', component: 'AbovePrompt', props: { ...PROPS, hasSurvey: true } })
  expect(await busy.find({ key: 'show-skills' })).toBeUndefined()
})
