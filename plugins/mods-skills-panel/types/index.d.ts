export type View = 'mods' | 'skills'

export type ModEntry = {
  name: string
  version?: string
  description: string
  source: string
  commands: string[]
  hooks: string[]
}

export type SkillEntry = {
  name: string
  source: string
  plugin?: string
  description: string
}

declare module 'claude-code' {
  interface PluginState {
    'mods-skills-panel': {
      view: View
      mods: ModEntry[]
      skills: SkillEntry[]
      usage: Record<string, number>
      models: Record<string, string>
      note: string
      expanded: string[]
    }
  }
}
