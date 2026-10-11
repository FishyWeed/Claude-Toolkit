export type Draft = string

declare module 'claude-code' {
  interface PluginState {
    'prompt-enhancer': { isBusy: boolean; original: Draft | null; model: string }
  }
}
