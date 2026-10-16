export const meta = {
  name: 'survey',
  description:
    'Reconnaissance for an optimization of TextFold: three read-only scouts take one goal apart from three different angles, then one agent merges what they found into a short list worth choosing from',
  whenToUse:
    'Called by the /optimize skill at its survey phase, when the goal spans more than one module and several approaches are plausible. Requires args {goal: "<what to optimize>"} — the calling session says what to optimize, since a workflow script has no filesystem access and cannot look for itself.',
  phases: [
    { title: 'Survey', detail: 'three read-only scouts, one goal, three angles, all independent' },
    { title: 'Rank', detail: 'merge what they found into one short list' },
  ],
}

// `args` may arrive as the caller's raw JSON string rather than the parsed
// object; normalize so both work. A string that is not valid JSON falls
// through and the requires-args check below reports it.
const ARGS = typeof args === 'string' ? (() => { try { return JSON.parse(args) } catch (e) { return {} } })() : (args || {})
const goal = ARGS.goal
if (!goal || typeof goal !== 'string' || !goal.trim()) {
  throw new Error('survey requires args: {goal: "<what to optimize>"} — say what to optimize before surveying for it')
}

const SCOUT_SCHEMA = {
  type: 'object',
  required: ['path', 'constraints', 'candidates'],
  properties: {
    path: {
      type: 'string',
      description: 'The files and functions this goal runs through, in the order the data flows, as path:line. Say how the modules hand off to each other.',
    },
    constraints: {
      type: 'array',
      items: { type: 'string' },
      description: 'Rules already written down that a change here must respect — quote the rule and name where it is written. 2-6 entries.',
    },
    candidates: {
      type: 'array',
      items: {
        type: 'object',
        required: ['title', 'files', 'whatChanges', 'benefit', 'cost', 'risk', 'howToVerify'],
        properties: {
          title: { type: 'string', description: 'What the change is, as a noun phrase' },
          files: { type: 'array', items: { type: 'string' }, description: 'Exact files it would touch' },
          whatChanges: { type: 'string', description: 'One or two sentences on what happens differently' },
          benefit: { type: 'string', description: 'What it buys, as something measurable where possible' },
          cost: { type: 'string', description: 'New code, new state, new failure modes' },
          risk: { type: 'string', description: 'What it could break that is not obvious' },
          howToVerify: { type: 'string', description: 'How you would prove it worked, and prove it broke nothing' },
        },
      },
      description: 'One to three CONCRETE candidate changes visible from this angle. Two well-founded ones beat five speculative ones.',
    },
    unresolved: {
      type: 'array',
      items: { type: 'string' },
      description: 'What you could not determine, and why. A guess presented as a fact is worse here than a gap.',
    },
  },
}

// Three angles on one goal. They are deliberately blind to each other: an
// angle that knows what the others found stops looking where they looked.
const ANGLES = [
  {
    key: 'the path',
    ask: `Follow the code this goal would change. Start from the entry point a user or a request reaches, and follow it to where the work actually happens. The candidates you propose are the ones visible from having read that path: a step that is unnecessary, an ordering that costs more than it needs to, work repeated that could be done once, a boundary crossed twice.`,
  },
  {
    key: 'the constraints',
    ask: `Work from what this repository has already written down about itself — docs/DEVELOPMENT.md, CONTRIBUTING.md, the tests, and the commit history around the files this goal concerns (git log -p on them is worth the time). The candidates you propose are the ones visible from the rules: something the stated design intends but the code does not do, a constraint that is being paid for on every call, a past fix that hints the same ground is still soft.`,
  },
  {
    key: 'the alternatives',
    ask: `Ignore how it is done today and ask how else this goal could be reached — a different module, a different algorithm, a cache, a config instead of code, doing it at parse time instead of render time, or not doing it at all because something upstream already answers it. The candidates you propose are the structurally different ones. Say plainly when the honest answer is that the existing approach is already the right one.`,
  },
]

log(`Surveying "${goal.trim()}" from ${ANGLES.length} angles`)

const found = await parallel(
  ANGLES.map((angle) => () =>
    agent(
      `An optimization of TextFold is being planned: "${goal.trim()}". You are investigating it from ONE angle — ${angle.key}.

${angle.ask}

Read docs/DEVELOPMENT.md first: its Layout section is the authoritative map of the modules, and its other sections state the constraints that are easy to break by accident. Then follow the angle you were given.

Return the path, the constraints, your candidates, and anything you could not determine. Do not propose a change you have not located in the code.`,
      {
        agentType: 'textfold-scout',
        label: `survey:${angle.key}`,
        phase: 'Survey',
        schema: SCOUT_SCHEMA,
      },
    ),
  ),
)

// Kept as pairs, not as a filtered array: dropping a failed scout would shift
// every later result onto the wrong angle.
const kept = []
found.forEach((result, i) => {
  if (result) kept.push({ angle: ANGLES[i].key, result })
})
const lost = ANGLES.filter((_, i) => !found[i]).map((a) => a.key)
if (lost.length) {
  log(`Not surveyed (agent skipped or errored): ${lost.join(', ')} — the short list is narrower for it`)
}
if (!kept.length) {
  throw new Error('every scout failed; nothing to rank — rerun before planning anything')
}

// Flattened here, in plain code, so the ranking agent sees each candidate once
// and does not spend its context re-deriving what the scouts already said.
const candidates = []
for (const { angle, result } of kept) {
  for (const c of result.candidates || []) {
    candidates.push({ ...c, angle })
  }
}
const constraints = kept.flatMap(({ result }) => result.constraints || [])
const unresolved = kept.flatMap(({ result }) => result.unresolved || [])

log(`${candidates.length} candidates from ${kept.length} angles, ranking them`)

const RANK_SCHEMA = {
  type: 'object',
  required: ['ranked', 'notRanked'],
  properties: {
    ranked: {
      type: 'array',
      items: {
        type: 'object',
        required: ['title', 'files', 'why', 'benefit', 'risk', 'howToVerify'],
        properties: {
          title: { type: 'string' },
          files: { type: 'array', items: { type: 'string' } },
          why: { type: 'string', description: 'Why this one, in one sentence — what makes it worth doing before the others' },
          benefit: { type: 'string' },
          risk: { type: 'string', description: 'Carried over from the scout, plus anything the ranking itself exposes' },
          howToVerify: { type: 'string' },
        },
      },
      description: 'The short list, best first. At most three.',
    },
    notRanked: {
      type: 'array',
      items: {
        type: 'object',
        required: ['title', 'whyNot'],
        properties: {
          title: { type: 'string' },
          whyNot: { type: 'string' },
        },
      },
      description: 'Everything dropped, and why. Never omit this: a rejected candidate that vanishes cannot be reconsidered.',
    },
    constraints: {
      type: 'array',
      items: { type: 'string' },
      description: 'The constraints the scouts agreed on, deduplicated. These are what the plan must respect.',
    },
    unresolved: {
      type: 'array',
      items: { type: 'string' },
      description: 'What nobody could determine — carry it forward so the plan does not quietly assume an answer.',
    },
  },
}

const ranked = await agent(
  `Three scouts investigated one optimization goal for TextFold from different angles and returned the candidates below. Merge them.

The goal was: "${goal.trim()}"

The candidates, each tagged with the angle that found it:
${JSON.stringify(candidates, null, 2)}

The constraints they found:
${JSON.stringify(constraints, null, 2)}

What they could not determine:
${JSON.stringify(unresolved, null, 2)}

Do this:
1. **Drop the duplicates.** Two scouts looking from different angles often land on the same change in different words. One entry, keeping the sharper of the two descriptions and the union of the files.
2. **Rank what remains.** Best first, at most three. Rank by how much is bought per unit of risk — a large win that could break something subtle is not obviously better than a small win that cannot.
3. **Say what you dropped and why.** Include the candidates that were duplicates of a kept one, and the ones that are simply not worth it.
4. **Do not invent a candidate none of them found.** If the list is thin, the answer is a thin list.`,
  {
    label: 'rank:candidates',
    phase: 'Rank',
    schema: RANK_SCHEMA,
  },
)

if (!ranked) {
  throw new Error('the ranking agent returned nothing; the candidates are below, unranked')
}

return {
  goal: goal.trim(),
  ranked: ranked.ranked || [],
  notRanked: ranked.notRanked || [],
  constraints: ranked.constraints || [],
  unresolved: ranked.unresolved || [],
  surveyedAngles: ANGLES.filter((_, i) => found[i]).map((a) => a.key),
}

