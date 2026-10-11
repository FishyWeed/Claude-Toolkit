export type RunStatus = 'running' | 'done' | 'failed'

export type SwarmRun = {
  /** The Agent tool call that started it. */
  id: string
  /** The subagent's loop id, once started; its tool calls carry it. */
  agentId?: string
  /** The specialist, without the plugin prefix: `researcher`, `slides-designer`, ... */
  agent: string
  /** The Agent call's short description of the task. */
  description: string
  status: RunStatus
  startedAt: number
  endedAt?: number
  /** Tool calls the specialist has made so far. */
  tools: number
  /** What it did last, e.g. `Write slides/deck.json`. */
  lastAction: string
}

declare module 'claude-code' {
  interface PluginState {
    swarm: {
      runs: SwarmRun[]
      /** Bumped every second while a run is going, so elapsed times redraw. */
      tick: number
    }
  }
}
