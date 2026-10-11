import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Route, Tier } from '../types'
import { AGENT_DEFAULTS, classify } from './classify'

const enabled = atom({ plugin: 'model-router', key: 'enabled' } as const, true)
const last = atom({ plugin: 'model-router', key: 'last' } as const, null as Route | null)
const overrides = atom({ plugin: 'model-router', key: 'overrides' } as const, {} as Record<string, Tier>)

const TIERS: readonly Tier[] = ['haiku', 'sonnet', 'opus']
const NAME: Record<Tier, string> = { haiku: 'Haiku', sonnet: 'Sonnet', opus: 'Opus' }
const isTier = (v: unknown): v is Tier => typeof v === 'string' && (TIERS as readonly string[]).includes(v)

const save = async ($: EngineInterface) => {
  await $.store.set('enabled', await read($, enabled))
  await $.store.set('overrides', await read($, overrides))
}

const statusText = async ($: EngineInterface) => {
  const on = await read($, enabled)
  const mine = await read($, overrides)
  const table = { ...AGENT_DEFAULTS, ...mine }
  const rows = Object.entries(table).map(([agent, m]) => `  ${agent}: ${NAME[m]}${agent in mine ? ' (yours)' : ''}`)
  return [
    `Model router: ${on ? 'Auto' : 'Off'}`,
    'Subagent models (others are picked from their task):',
    ...rows,
    'Change: /router on | off | set <agent> <haiku|sonnet|opus|default>. Start a prompt with ~ to skip routing once.',
  ].join('\n')
}

export const register: Register = on => {
  // The model picked for the current main reply; cleared when the reply ends.
  let turnModel: Tier | undefined

  on('session.start', async ($, e, next) => {
    const savedOn = await $.store.get('enabled').catch(() => undefined)
    const savedOverrides = await $.store.get('overrides').catch(() => undefined)
    if (typeof savedOn === 'boolean') await update($, enabled, () => savedOn)
    if (savedOverrides && typeof savedOverrides === 'object') {
      const clean = Object.fromEntries(
        Object.entries(savedOverrides as Record<string, unknown>).filter(([, v]) => isTier(v)),
      ) as Record<string, Tier>
      await update($, overrides, () => clean)
    }
    await $.command.register({ name: 'router', description: 'Show or change the model router: on, off, or set a subagent model' })
    return next(e)
  })

  on('command.run', { command: 'router' }, async ($, e) => {
    const [verb, agent, model] = e.args.trim().split(/\s+/)
    if (!verb) return { text: await statusText($) }
    if (verb === 'on' || verb === 'off') {
      await update($, enabled, () => verb === 'on')
      await save($)
      return { text: `Model router: ${verb === 'on' ? 'Auto' : 'Off'}` }
    }
    if (verb === 'set' && agent && (isTier(model) || model === 'default')) {
      await update($, overrides, o => {
        const copy = { ...o }
        if (model === 'default') delete copy[agent]
        else copy[agent] = model
        return copy
      })
      await save($)
      return { text: model === 'default' ? `${agent} is back to its default.` : `${agent} will run on ${NAME[model as Tier]}.` }
    }
    return { text: 'Use /router, /router on, /router off, or /router set <agent> <haiku|sonnet|opus|default>' }
  })

  // Pick the model for the person's own prompts.
  on('prompt.submit', async ($, e, next) => {
    if (e.origin.kind !== 'composer' || !(await read($, enabled))) return next(e)
    const skip = e.text.startsWith('~')
    const verdict = skip ? null : classify(e.text)
    turnModel = verdict?.model
    // Always overwrite, so a prompt with no pick never shows the previous prompt's model.
    await update($, last, () => (verdict ? { where: 'prompt', model: verdict.model, reason: verdict.reason } : null))
    return next(skip ? { ...e, text: e.text.slice(1).trimStart() } : e)
  }).catch(($, e, next) => next(e))

  // Run each step of the main reply on the picked model. Subagents are routed below.
  on('turn.step', async function* ($, e, next) {
    if (turnModel && !e.agentId && e.model !== turnModel) return yield* next({ ...e, model: turnModel })
    return yield* next(e)
  })

  on('turn.complete', (_$, e, next) => {
    if (!e.agentId) turnModel = undefined
    return next(e)
  })

  // Give every subagent a model unless Claude chose one on purpose.
  on('tool.call', { tool: 'Agent' }, async ($, e, next) => {
    if (e.model || e.subagent_type === 'fork' || !(await read($, enabled))) return next(e)
    const type = e.subagent_type ?? 'general-purpose'
    const mine = await read($, overrides)
    const fixed = mine[type] ?? AGENT_DEFAULTS[type]
    // The short description says what kind of task it is; the full prompt is the fallback.
    const verdict = fixed ? { model: fixed, reason: `${type} default` } : (classify(e.description) ?? classify(e.prompt))
    if (!verdict) return next(e)
    await update($, last, () => ({ where: type, model: verdict.model, reason: verdict.reason }))
    return next({ ...e, model: verdict.model })
  }).catch(($, e, next) => next(e))

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const rest = await next(e)
    if (e.props.hasSurvey) return rest

    const { Box, Select } = $.ui.resolve(e)
    const isOn = await read($, enabled)
    const route = await read($, last)

    return (
      <Box flexDirection="row" flexWrap="wrap" alignItems="center" columnGap={2}>
        <Select
          key="router"
          label="Router"
          options={[
            // The picked model rides in the option label so the strip stays one row.
            { value: 'auto', label: route?.where === 'prompt' ? `Auto · ${NAME[route.model]}` : 'Auto' },
            { value: 'off', label: 'Off' },
          ]}
          value={isOn ? 'auto' : 'off'}
          onSelect={async v => {
            await update($, enabled, () => v === 'auto')
            await save($)
          }}
        />
        {rest}
      </Box>
    )
  })
}
