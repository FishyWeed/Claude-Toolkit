import { describe, expect, test } from 'claude-code/testing'
import type { On } from 'claude-code'

const SURFACES = ['terminal', 'desktop'] as const
const USAGE = { input_tokens: 1, output_tokens: 1, cache_read_input_tokens: 0, cache_creation_input_tokens: 0 }
const PROPS = { hasSurvey: false, isWorking: false, maxRows: 10, bodyColumns: 80, scroll: { offset: 0, bodyRows: 10 }, view: {} }

// A fake prompt box, model and send, standing in for the engine beneath the mod.
const fakeEngine = (on: On, initial: string, reply: string) => {
  const box = { text: initial, sent: [] as string[], asked: [] as string[], models: [] as string[], toasts: [] as string[] }
  on('prompt.read', () => ({ value: { text: box.text, cursor: box.text.length } }))
  on('prompt.fill', ($, e) => {
    box.text = e.text
    return { isFilled: true }
  })
  on('prompt.submit', ($, e) => {
    box.sent.push(e.text)
    return { text: e.text }
  })
  on('model.complete', ($, e) => {
    box.asked.push(e.prompt)
    box.models.push(e.model)
    return { value: { isAnswered: true, text: reply, usage: USAGE } }
  })
  // Stands in for what other mods draw in the same strip.
  on('ui.render', ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    return <Box><Text>other-mod</Text></Box>
  })
  on('ui.toast', ($, e) => {
    box.toasts.push(String(e.text))
    return { value: undefined }
  })
  return box
}

describe('prompt-enhancer', () => {
  for (const surface of SURFACES) {
    test(`${surface}: Enhance rewrites the draft in place without sending it`, async ($, on) => {
      const box = fakeEngine(on, 'fix login bug', '```\nFind and fix the login bug.\n```')
      const ui = await $.ui.mount({ plugin: 'prompt-enhancer', surface, component: 'AbovePrompt', props: PROPS })

      expect(await ui.find({ key: 'enhance' })).toBeDefined()
      expect(await ui.find({ key: 'undo' })).toBeUndefined()
      // Other mods' part of the strip is kept beside ours.
      expect(await ui.find({ type: 'Text', text: 'other-mod' })).toBeDefined()

      await ui.press({ key: 'enhance' })

      expect(box.asked[0]).toContain('fix login bug')
      expect(box.text).toBe('Find and fix the login bug.')
      expect(box.sent).toEqual([])

      await ui.press({ key: 'undo' })
      expect(box.text).toBe('fix login bug')
      expect(await ui.find({ key: 'undo' })).toBeUndefined()
    })

    test(`${surface}: the model picker chooses and saves the model`, async ($, on) => {
      const saved: Record<string, unknown> = {}
      on('store.get', ($, e) => ({ value: saved[e.key] }))
      on('store.set', ($, e) => {
        saved[e.key] = e.value
        return { value: undefined }
      })
      const box = fakeEngine(on, 'summarise this', 'Summarise this text in three bullet points.')
      const ui = await $.ui.mount({ plugin: 'prompt-enhancer', surface, component: 'AbovePrompt', props: PROPS })

      await ui.press({ key: 'enhance' })
      expect(box.models).toEqual(['sonnet'])

      await ui.select({ key: 'model', value: 'haiku' })
      await ui.press({ key: 'undo' })
      await ui.press({ key: 'enhance' })

      expect(box.models).toEqual(['sonnet', 'haiku'])
      expect(saved.model).toBe('haiku')
    })

    test(`${surface}: an empty draft is left alone`, async ($, on) => {
      const box = fakeEngine(on, '   ', 'should not be used')
      const ui = await $.ui.mount({ plugin: 'prompt-enhancer', surface, component: 'AbovePrompt', props: PROPS })

      await ui.press({ key: 'enhance' })

      expect(box.asked).toEqual([])
      expect(box.text).toBe('   ')
      expect(box.toasts.length).toBe(1)
    })
  }
})
