import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { ModEntry, SkillEntry, View } from '../types'

const NAME = 'mods-skills-panel'
const PANE = 'mods-skills'
const TITLE = 'Mods & Skills'

// Model choices a row cycles through. "default" means: leave the session's model alone.
const MODELS = ['default', 'opus', 'sonnet', 'haiku'] as const
const MODEL_LABEL: Record<string, string> = {
  default: 'Default',
  opus: 'Opus',
  sonnet: 'Sonnet',
  haiku: 'Haiku',
}

// Colors are theme keys, so they follow the person's light or dark theme.
const MODEL_COLOR: Record<string, string> = {
  opus: 'claude',
  sonnet: 'suggestion',
  haiku: 'success',
}

// Where an item came from: its card border, name and tag share this color.
const SOURCE_STYLE: Record<string, { label: string; color: string }> = {
  'in development': { label: 'in development', color: 'warning' },
  installed: { label: 'installed', color: 'success' },
  loaded: { label: 'loaded', color: 'suggestion' },
  plugin: { label: 'plugin', color: 'merged' },
  userSettings: { label: 'personal', color: 'success' },
  projectSettings: { label: 'project', color: 'planMode' },
  'built-in': { label: 'built-in', color: 'suggestion' },
  bundled: { label: 'built-in', color: 'suggestion' },
  mcp: { label: 'MCP', color: 'ide' },
  syncedSkills: { label: 'synced', color: 'autoAccept' },
}
const sourceStyle = (kind: string) => SOURCE_STYLE[kind] ?? { label: kind, color: 'subtle' }

// Usage reads at a glance: unused is faded, used is accented, heavily used stands out.
const usageColor = (used: number) => (used === 0 ? 'inactive' : used < 10 ? 'text' : 'claude')

const view = atom({ plugin: 'mods-skills-panel', key: 'view' } as const, 'mods' as View)
const mods = atom({ plugin: 'mods-skills-panel', key: 'mods' } as const, [] as ModEntry[])
const skills = atom({ plugin: 'mods-skills-panel', key: 'skills' } as const, [] as SkillEntry[])
const usage = atom({ plugin: 'mods-skills-panel', key: 'usage' } as const, {} as Record<string, number>)
const models = atom({ plugin: 'mods-skills-panel', key: 'models' } as const, {} as Record<string, string>)
const note = atom({ plugin: 'mods-skills-panel', key: 'note' } as const, '')
// Rows showing their details; every other row is one numbered line.
const expanded = atom({ plugin: 'mods-skills-panel', key: 'expanded' } as const, [] as string[])

const modKey = (name: string) => `mod:${name}`
const skillKey = (name: string) => `skill:${name}`

// Plugins seen joining the chain, kept for the session's refreshes.
const seenPlugins = new Map<string, { version?: string; provenance: string; hooks: string[] }>()

async function bump($: EngineInterface, key: string) {
  const next = await update($, usage, all => ({ ...all, [key]: (all[key] ?? 0) + 1 }))
  await $.store.set('usage', next).catch(() => undefined)
}

async function readManifest($: EngineInterface, dir: string) {
  try {
    const text = await $.fs.read(`${dir}/.claude-plugin/plugin.json`)
    const json = JSON.parse(typeof text === 'string' ? text : '') as {
      name?: string
      version?: string
      description?: string
    }
    return json.name ? json : undefined
  } catch {
    return undefined
  }
}

// Finds plugin folders (ones holding .claude-plugin/plugin.json) up to `depth` levels down.
async function findPluginDirs($: EngineInterface, root: string, depth: number): Promise<string[]> {
  if (depth < 0 || !(await $.fs.exists(root).catch(() => false))) return []
  if (await $.fs.exists(`${root}/.claude-plugin/plugin.json`).catch(() => false)) return [root]
  const entries = await $.fs.list(root).catch(() => [])
  const found: string[] = []
  for (const entry of entries) {
    if (entry.kind !== 'dir' || entry.name.startsWith('.') || entry.name === 'node_modules') continue
    found.push(...(await findPluginDirs($, `${root}/${entry.name}`, depth - 1)))
  }
  return found
}

async function refresh($: EngineInterface) {
  const commands = await $.command.list().catch(() => [])
  const describe = new Map(commands.map(c => [c.name, c.description]))

  // Mods: plugins on disk, plugins seen loading, and plugins that own slash commands.
  const byName = new Map<string, ModEntry>()
  const add = (name: string, patch: Partial<ModEntry>) => {
    const had = byName.get(name) ?? { name, description: '', source: 'loaded', commands: [], hooks: [] }
    byName.set(name, {
      ...had,
      ...Object.fromEntries(Object.entries(patch).filter(([, v]) => v !== undefined && v !== '')),
      commands: [...new Set([...had.commands, ...(patch.commands ?? [])])],
      hooks: [...new Set([...had.hooks, ...(patch.hooks ?? [])])],
    })
  }

  const home = (await $.env.get('HOME').catch(() => undefined)) ?? '/root'
  const devRoot = $.plugin.root.slice(0, $.plugin.root.lastIndexOf('/'))
  const roots: [string, string, number][] = [
    [devRoot, 'in development', 1],
    [`${home}/.claude/plugins`, 'installed', 5],
  ]
  for (const [root, source, depth] of roots) {
    for (const dir of await findPluginDirs($, root, depth)) {
      const manifest = await readManifest($, dir)
      if (manifest?.name) {
        add(manifest.name, { version: manifest.version, description: manifest.description, source })
      }
    }
  }
  for (const [name, info] of seenPlugins) {
    if (info.provenance.endsWith('@builtin')) continue
    add(name, { version: info.version, hooks: info.hooks })
  }
  for (const c of commands) {
    if (c.source === 'plugin' && c.plugin) add(c.plugin, { commands: [c.name] })
  }
  for (const mod of byName.values()) {
    if (!mod.description) mod.description = 'No description in its manifest.'
  }

  // Skills: the listing the model is given, described from the slash-command list.
  const measured = await $.session.usage({ breakdown: 'summary' }).catch(() => undefined)
  const listed = measured?.context.breakdown?.skills?.skillFrontmatter ?? []
  const skillList: SkillEntry[] = listed.map(s => {
    const short = s.name.includes(':') ? s.name.slice(s.name.indexOf(':') + 1) : s.name
    return {
      name: s.name,
      source: s.pluginName ? `plugin ${s.pluginName}` : s.source,
      plugin: s.pluginName,
      description: describe.get(s.name) ?? describe.get(short) ?? 'No description listed.',
    }
  })

  const sortByName = <T extends { name: string }>(list: T[]) =>
    [...list].sort((a, b) => a.name.localeCompare(b.name))
  await update($, mods, () => sortByName([...byName.values()]))
  await update($, skills, () => sortByName(skillList))
  const time = new Date(await $.clock.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  await update($, note, () => `Updated ${time}`)
}

async function toggle($: EngineInterface, key: string) {
  await update($, expanded, open => (open.includes(key) ? open.filter(k => k !== key) : [...open, key]))
}

async function cycleModel($: EngineInterface, key: string) {
  const all = await read($, models)
  const current = all[key] ?? 'default'
  const nextModel: string = MODELS[(MODELS.indexOf(current as (typeof MODELS)[number]) + 1) % MODELS.length] ?? 'default'
  const saved = await update($, models, list => {
    const copy = { ...list }
    if (nextModel === 'default') delete copy[key]
    else copy[key] = nextModel
    return copy
  })
  await $.store.set('models', saved).catch(() => undefined)
}

export const register: Register = on => {
  // The model a skill asked for, applied to the main loop's requests until its turn ends.
  let turnModel: string | undefined

  on('plugin.register', (_$, e, next) => {
    seenPlugins.set(e.name, { version: e.version, provenance: e.provenance, hooks: [...e.uses.events] })
    return next(e)
  }).catch((_$, e, next) => next(e))

  on('session.start', async ($, e, next) => {
    const result = await next(e)
    const savedUsage = (await $.store.get('usage').catch(() => undefined)) as Record<string, number> | undefined
    const savedModels = (await $.store.get('models').catch(() => undefined)) as Record<string, string> | undefined
    if (savedUsage) await update($, usage, () => savedUsage)
    if (savedModels) await update($, models, () => savedModels)
    seenPlugins.set(NAME, { provenance: `${NAME}@inline`, hooks: [] })
    await $.command.register({
      name: 'mods-skills',
      description: 'Open the Mods & Skills panel',
    })
    void refresh($).catch(() => undefined)
    void $.ui.open({ id: PANE, title: TITLE })
    return result
  })

  on('command.run', { command: 'mods-skills' }, async $ => {
    await refresh($).catch(() => undefined)
    await $.ui.open({ id: PANE, title: TITLE })
    return { text: 'Mods & Skills panel opened.' }
  })

  // Usage: a slash command that belongs to a mod counts as one use of that mod.
  on('command.run', async ($, e, next) => {
    if (e.command !== 'mods-skills') {
      const owner = (await read($, mods)).find(m => m.commands.includes(e.command))
      if (owner) await bump($, modKey(owner.name))
    }
    return next(e)
  }).catch((_$, e, next) => next(e))

  // Usage and model for skills: every expansion (/name, the Skill tool, a preload).
  on('skill.prompt', async ($, e, next) => {
    await bump($, skillKey(e.skill))
    const assigned = (await read($, models))[skillKey(e.skill)]
    if (assigned) turnModel = assigned
    return next(e)
  })

  on('turn.step', async function* ($, e, next) {
    if (turnModel && !e.agentId && e.model !== turnModel) {
      return yield* next({ ...e, model: turnModel })
    }
    return yield* next(e)
  })

  on('turn.complete', (_$, e, next) => {
    if (!e.agentId) turnModel = undefined
    return next(e)
  })

  // Model and usage for mods: a completion a mod asks for runs on its assigned model.
  on('model.complete', async ($, e, next) => {
    const origin = next.origin.plugin
    if (origin === NAME || origin === 'engine') return next(e)
    const known = (await read($, mods)).some(m => m.name === origin)
    if (!known) return next(e)
    await bump($, modKey(origin))
    const assigned = (await read($, models))[modKey(origin)]
    return next(assigned ? { ...e, model: assigned } : e)
  }).catch((_$, e, next) => next(e))

  // Skills / Mods buttons above the prompt, each opening the panel on that list.
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const rest = await next(e)
    if (e.props.hasSurvey) return rest

    const { Box, Button, Text } = $.ui.resolve(e)
    const show = async (list: View) => {
      await update($, view, () => list)
      await refresh($).catch(() => undefined)
      await $.ui.open({ id: PANE, title: TITLE })
    }

    return (
      <Box>
        <Button key="show-skills" label="🧩 Skills" onPress={() => show('skills')} />
        <Text> </Text>
        <Button key="show-mods" label="🛠 Mods" onPress={() => show('mods')} />
        <Text>  </Text>
        {rest}
      </Box>
    )
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const current = await read($, view)
    const modList = await read($, mods)
    const skillList = await read($, skills)
    const counts = await read($, usage)
    const assigned = await read($, models)
    const status = await read($, note)
    const openKeys = await read($, expanded)

    const rows =
      current === 'mods'
        ? modList.map(m => ({
            key: modKey(m.name),
            name: m.name,
            style: sourceStyle(m.source),
            meta: m.version ? `v${m.version}` : '',
            description: m.description,
            commands: m.commands.map(c => `/${c}`).join(', '),
          }))
        : skillList.map(s => ({
            key: skillKey(s.name),
            name: s.name,
            style: sourceStyle(s.plugin ? 'plugin' : s.source),
            meta: s.plugin ?? '',
            description: s.description,
            commands: '',
          }))

    const numberWidth = String(Math.max(1, rows.length)).length

    // A legend of the sources on screen, so each color is named once.
    const legend = [...new Map(rows.map(r => [r.style.label, r.style])).values()]

    const empty =
      current === 'mods'
        ? 'No mods found yet. Press Refresh after installing one.'
        : 'No skills listed in this session yet. Press Refresh.'

    return (
      <Box flexDirection="column" gap={1}>
        <Box flexDirection="row" gap={1} flexWrap="wrap">
          <Button
            key="tab-mods"
            label={`Mods (${modList.length})`}
            variant={current === 'mods' ? 'primary' : 'secondary'}
            hotkey="m"
            onPress={() => update($, view, () => 'mods')}
          />
          <Button
            key="tab-skills"
            label={`Skills (${skillList.length})`}
            variant={current === 'skills' ? 'primary' : 'secondary'}
            hotkey="s"
            onPress={() => update($, view, () => 'skills')}
          />
          <Button key="refresh" label="Refresh" hotkey="r" dimColor onPress={() => void refresh($)} />
        </Box>
        {status !== '' && <Text dimColor>{status}</Text>}
        {legend.length > 0 && (
          <Box flexDirection="row" gap={2} flexWrap="wrap">
            {legend.map(s => (
              <Text key={`legend-${s.label}`} color={s.color}>
                ● {s.label}
              </Text>
            ))}
          </Box>
        )}
        {rows.length === 0 && <Text dimColor>{empty}</Text>}
        {openKeys.length > 0 && (
          <Button key="collapse-all" label="Collapse all" hotkey="x" dimColor onPress={() => update($, expanded, () => [])} />
        )}
        <Box flexDirection="column">
          {rows.map((row, i) => {
            const isOpen = openKeys.includes(row.key)
            const model = assigned[row.key] ?? 'default'
            const used = counts[row.key] ?? 0
            const number = `${String(i + 1).padStart(numberWidth, ' ')}.`
            return (
              <Box key={row.key} flexDirection="column">
                {/* The line: number, arrow and name; a click opens or closes the details. */}
                <Button key={`row-${row.key}`} plain onPress={() => toggle($, row.key)}>
                  <Text dimColor>{number} </Text>
                  <Text color={row.style.color}>{isOpen ? '▾' : '▸'} </Text>
                  <Text bold color={row.style.color}>
                    {row.name}
                  </Text>
                  {model !== 'default' && <Text color={MODEL_COLOR[model] ?? 'text'}> ●</Text>}
                </Button>
                {isOpen && (
                  <Box
                    flexDirection="column"
                    borderStyle="round"
                    borderColor={row.style.color}
                    paddingX={1}
                    marginLeft={numberWidth + 2}
                    marginBottom={1}
                  >
                    <Box flexDirection="row" gap={1} flexWrap="wrap">
                      <Text color={row.style.color}>● {row.style.label}</Text>
                      {row.meta !== '' && <Text dimColor>{row.meta}</Text>}
                    </Box>
                    <Text wrap="wrap">{row.description}</Text>
                    {row.commands !== '' && (
                      <Text wrap="wrap">
                        <Text dimColor>Commands: </Text>
                        <Text color="permission">{row.commands}</Text>
                      </Text>
                    )}
                    <Box flexDirection="row" gap={1} flexWrap="wrap" alignItems="center">
                      <Text color={usageColor(used)} bold={used >= 10}>
                        {used === 1 ? 'Used 1 time' : `Used ${used} times`}
                      </Text>
                      {model !== 'default' && <Text color={MODEL_COLOR[model] ?? 'text'}>●</Text>}
                      <Button
                        key={`model-${row.key}`}
                        label={`Model: ${MODEL_LABEL[model] ?? model}`}
                        variant={model === 'default' ? 'secondary' : 'primary'}
                        onPress={() => cycleModel($, row.key)}
                      />
                    </Box>
                  </Box>
                )}
              </Box>
            )
          })}
        </Box>
      </Box>
    )
  })
}
