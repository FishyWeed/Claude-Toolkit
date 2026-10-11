import type { Tier } from '../types'

export type Verdict = { model: Tier; reason: string } | null

type Rule = readonly [RegExp, string]

// Deep work: reasoning across code or systems, or anything high-stakes.
const DEEP: readonly Rule[] = [
  [/\b(debug|root cause|stack ?trace|flaky|regression|race condition|deadlock|memory leak)\b/, 'debugging'],
  [/\bwhy (is|does|do|did|are)\b.*\b(fail|failing|broken|crash|slow|wrong|error)/, 'debugging'],
  [/\b(architect|architecture|system design|trade-?offs?|redesign|rfc|design doc)\b/, 'architecture'],
  [/\b(refactor|migrat(e|ion)|rewrite|overhaul)\b/, 'large change'],
  [/\b(security|vulnerab|audit|threat model)\b/, 'security'],
  [/\b(investigate|deep dive|research|analy[sz]e|compare)\b/, 'research and analysis'],
  [/\b(plan|strategy|roadmap)\b/, 'planning'],
  [/\b(optimi[sz]e|performance|bottleneck)\b/, 'performance'],
  [/\breview (the |this |my )?(code|pr|pull request|diff|branch)\b/, 'code review'],
]

// Mechanical work: short, well-defined, little judgement.
const QUICK: readonly Rule[] = [
  [/\b(typo|rename|reformat|format|lint|prettier)\b/, 'mechanical edit'],
  [/\b(commit message|git (add|commit|push|pull|status|log|checkout|branch)|bump (the )?version)\b/, 'git chore'],
  [/^(list|show|print|count|sort|find|locate) /, 'quick lookup'],
  [/\b(list|find|locate|count) (all )?(the )?(files|folders|directories|usages|references)\b/, 'quick lookup'],
  [/^(what's|what is|what are|where is|which) /, 'quick question'],
  [/\b(convert|translate) /, 'conversion'],
]

// Everyday coding.
const STANDARD: readonly Rule[] = [
  [/\b(implement|add|create|write|build|make|update|change|edit|fix|test|function|component|endpoint|script|feature|bug)\b/, 'coding'],
]

const match = (rules: readonly Rule[], text: string) => rules.find(([re]) => re.test(text))?.[1]

/** Picks a model tier for a piece of work, or null when the text gives no clear signal. */
export const classify = (raw: string): Verdict => {
  const text = raw.trim().toLowerCase()
  if (!text) return null

  const deep = match(DEEP, text)
  if (deep) return { model: 'opus', reason: deep }
  if (text.length > 2000) return { model: 'opus', reason: 'long, detailed request' }

  const quick = match(QUICK, text)
  if (quick && text.length < 200) return { model: 'haiku', reason: quick }

  const standard = match(STANDARD, text)
  if (standard) return { model: 'sonnet', reason: standard }

  return null
}

/** Default models for known subagent types. Anything else is classified from its task. */
export const AGENT_DEFAULTS: Record<string, Tier> = {
  'swarm:researcher': 'sonnet',
  'swarm:data-analyst': 'sonnet',
  'swarm:docs-writer': 'sonnet',
  'swarm:slides-designer': 'sonnet',
  'swarm:video-maker': 'sonnet',
  'swarm:image-maker': 'haiku',
  Explore: 'haiku',
  'claude-code-guide': 'haiku',
  Plan: 'opus',
}
