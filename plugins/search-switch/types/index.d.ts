export type SearchMode = 'native' | 'exa'

declare module 'claude-code' {
  interface PluginState {
    'search-switch': { mode: SearchMode }
  }
}
