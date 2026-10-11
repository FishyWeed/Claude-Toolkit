export type Tier = 'haiku' | 'sonnet' | 'opus'
export type Route = { where: string; model: Tier; reason: string }

declare module 'claude-code' {
  interface PluginState {
    'model-router': { enabled: boolean; last: Route | null; overrides: Record<string, Tier> }
  }
}
