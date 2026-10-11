import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register, Timer } from 'claude-code'

import type { RunStatus, SwarmRun } from '../types'

const PANE = 'swarm'
const TITLE = 'Swarm'
const PREFIX = 'swarm:'

const runs = atom({ plugin: 'swarm', key: 'runs' } as const, [] as SwarmRun[])
const tick = atom({ plugin: 'swarm', key: 'tick' } as const, 0)

// Each specialist keeps one colour, so a glance tells who is doing what.
const AGENT_STYLE: Record<string, { label: string; color: string }> = {
  researcher: { label: 'Research', color: 'suggestion' },
  'data-analyst': { label: 'Data', color: 'merged' },
  'slides-designer': { label: 'Slides', color: 'claude' },
  'docs-writer': { label: 'Docs', color: 'planMode' },
  'image-maker': { label: 'Images', color: 'autoAccept' },
  'video-maker': { label: 'Video', color: 'warning' },
}
const agentStyle = (agent: string) => AGENT_STYLE[agent] ?? { label: agent, color: 'subtle' }

const STATUS_STYLE: Record<RunStatus, { glyph: string; color: string }> = {
  running: { glyph: '●', color: 'warning' },
  done: { glyph: '✓', color: 'success' },
  failed: { glyph: '✗', color: 'error' },
}

const basename = (path: string) => path.split(/[\\/]/).filter(Boolean).pop() ?? path

/** A few words for what a tool call does, from its arguments. */
function describe(e: Record<string, unknown>): string {
  const tool = String(e.tool ?? '')
  const str = (key: string) => (typeof e[key] === 'string' ? (e[key] as string) : '')
  if (str('file_path')) return `${tool} ${basename(str('file_path'))}`
  if (tool === 'Bash' || tool === 'PowerShell') return str('description') || str('command').slice(0, 60)
  if (str('query')) return `${tool} "${str('query').slice(0, 50)}"`
  if (str('url')) {
    const host = /^[a-z]+:\/\/([^/]+)/i.exec(str('url'))?.[1]
    return `${tool} ${host ?? str('url').slice(0, 50)}`
  }
  if (str('skill')) return `Skill ${str('skill')}`
  if (str('pattern')) return `${tool} ${str('pattern').slice(0, 50)}`
  return tool
}

function formatElapsed(ms: number): string {
  const total = Math.max(0, Math.round(ms / 1000))
  const m = Math.floor(total / 60)
  const s = total % 60
  return m > 0 ? `${m}m ${String(s).padStart(2, '0')}s` : `${s}s`
}

// Redraws elapsed times once a second while something runs; stops when all are finished.
let ticker: Timer | undefined

async function keepTicking($: EngineInterface) {
  const anyRunning = (await read($, runs)).some(r => r.status === 'running')
  if (anyRunning && !ticker) {
    ticker = $.clock.every(1000, () => void onTick($))
  }
}

async function onTick($: EngineInterface) {
  await update($, tick, n => n + 1)
  const list = await read($, runs)
  if (!list.some(r => r.status === 'running')) {
    ticker?.cancel()
    ticker = undefined
  }
}

async function patch($: EngineInterface, match: (r: SwarmRun) => boolean, fn: (r: SwarmRun) => SwarmRun) {
  await update($, runs, list => list.map(r => (match(r) ? fn(r) : r)))
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const result = await next(e)
    await $.command.register({ name: 'swarm-panel', description: 'Show the swarm progress panel' })
    return result
  })

  on('command.run', { command: 'swarm-panel' }, async $ => {
    await $.ui.open({ id: PANE, title: TITLE })
    return { text: 'Swarm panel opened.' }
  })

  // A specialist starts: add its row and bring the panel up.
  on('agent.spawn', async ($, e, next) => {
    if (!e.subagentType.startsWith(PREFIX)) return next(e)
    const run: SwarmRun = {
      id: e.tool_use_id,
      agent: e.subagentType.slice(PREFIX.length),
      description: e.description,
      status: 'running',
      startedAt: await $.clock.now(),
      tools: 0,
      lastAction: 'starting',
    }
    await update($, runs, list => [...list.filter(r => r.id !== run.id), run].slice(-50))
    void $.ui.open({ id: PANE, title: TITLE })
    await keepTicking($)
    const started = await next(e)
    if ('deny' in started && started.deny !== undefined) {
      const at = await $.clock.now()
      await patch($, r => r.id === run.id, r => ({ ...r, status: 'failed', endedAt: at, lastAction: started.deny ?? 'refused' }))
    } else if (started.agentId) {
      await patch($, r => r.id === run.id, r => ({ ...r, agentId: started.agentId }))
    }
    return started
  }).catch((_$, e, next) => next(e))

  // Its tool calls: count them and show the latest.
  on('tool.call', async ($, e, next) => {
    if (e.agentId) {
      const list = await read($, runs)
      if (list.some(r => r.agentId === e.agentId)) {
        const action = describe(e as unknown as Record<string, unknown>)
        await patch($, r => r.agentId === e.agentId, r => ({ ...r, tools: r.tools + 1, lastAction: action, status: 'running', endedAt: undefined }))
        await keepTicking($)
      }
    }
    return next(e)
  }).catch((_$, e, next) => next(e))

  // Its loop ends: done, or failed with the reason.
  on('turn.complete', async ($, e, next) => {
    const result = await next(e)
    if (e.agentId) {
      const status: RunStatus = e.reason === 'answer' ? 'done' : 'failed'
      const at = await $.clock.now()
      const why = e.reason === 'answer' ? 'finished' : e.reason
      await patch($, r => r.agentId === e.agentId, r => ({ ...r, status, endedAt: at, lastAction: status === 'done' ? r.lastAction : why }))
    }
    return result
  }).catch((_$, e, next) => next(e))

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const list = await read($, runs)
    await read($, tick)
    const now = await $.clock.now()
    const counts = { running: 0, done: 0, failed: 0 }
    for (const r of list) counts[r.status]++
    const room = Math.max(1, Math.floor(((e.viewport?.rows ?? 30) - 4) / 3))

    return (
      <Box flexDirection="column" gap={1}>
        <Box flexDirection="row" gap={2} flexWrap="wrap" alignItems="center">
          <Text color="warning">● {counts.running} running</Text>
          <Text color="success">✓ {counts.done} done</Text>
          <Text color={counts.failed > 0 ? 'error' : 'inactive'}>✗ {counts.failed} failed</Text>
          {counts.done + counts.failed > 0 && (
            <Button
              key="clear"
              label="Clear finished"
              hotkey="c"
              dimColor
              onPress={() => update($, runs, all => all.filter(r => r.status === 'running'))}
            />
          )}
        </Box>
        {list.length === 0 && <Text dimColor>No swarm agents yet. Run /swarm with what you want made.</Text>}
        {list.slice(-room).map(r => {
          const who = agentStyle(r.agent)
          const st = STATUS_STYLE[r.status]
          const elapsed = formatElapsed((r.endedAt ?? now) - r.startedAt)
          return (
            <Box key={r.id} flexDirection="column">
              <Box flexDirection="row" gap={1}>
                <Text color={st.color} bold>
                  {st.glyph}
                </Text>
                <Text color={who.color} bold>
                  {who.label}
                </Text>
                <Text wrap="truncate-end">{r.description}</Text>
              </Box>
              <Box flexDirection="row" gap={1} paddingLeft={2}>
                <Text dimColor>
                  {elapsed} · {r.tools === 1 ? '1 step' : `${r.tools} steps`} ·
                </Text>
                <Text color={r.status === 'failed' ? 'error' : undefined} dimColor={r.status !== 'failed'} wrap="truncate-end">
                  {r.lastAction}
                </Text>
              </Box>
            </Box>
          )
        })}
      </Box>
    )
  })
}
