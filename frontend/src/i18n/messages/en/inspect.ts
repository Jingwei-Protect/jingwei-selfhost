import { inspectReport } from './inspectReport'

export const inspect = {
  betaBadge: 'Beta',
  title: 'AI Inspect Assist',
  metaDescription:
    'Jingwei AI Inspect Assist (Beta): upload an image for auxiliary clues—provenance, file structure, pixel stats. No final verdict; for creator reference only.',
  subtitle: 'Upload an image to review auxiliary clues in the report (no final verdict)',
  principlesCard: {
    title: 'How this analysis works',
    intro: 'This page builds an inspection report from readable signals in the file: provenance proofs, save history, file structure, and pixel statistics.',
  },
  unlock: {
    intro: 'AI Inspect Assist is in closed beta. Enter the beta code provided by the admin.',
    codeLabel: 'Beta code',
    codePlaceholder: 'Enter beta code',
    checking: 'Verifying…',
    enter: 'Enter Beta',
    invalid: 'Invalid beta code',
  },
  principles: {
    expand: 'Expand: how this works',
    collapse: 'Collapse: how this works',
    bodyLead:
      'This page builds an inspection report from what the file still carries: provenance proofs, save history, file structure, and pixel statistics. It does not hand down a verdict on whether the image is AI-generated — each line below is for manual comparison.',
    bodyBullet1:
      'Each item lists a basic analysis and what was found. Red badges mark stronger clues.',
    bodyBullet2:
      'A missing item does not prove the opposite. Images from social platforms often lose metadata after re-encoding — that means "not found," not "definitely human-made."',
    interpretationLabel: 'Interpretation',
    statsHint: 'Statistical hints (reference only)',
    metricsTitle: 'Raw measurements',
  },
  actions: {
    recheck: 'Re-run check',
    checking: 'Checking…',
  },
  loading: {
    reading: 'Reading provenance credentials and metadata…',
    failed: 'Inspection failed',
    network: 'Network error',
  },
  strengthLabels: {
    strong: 'Hard evidence',
    medium: 'Structural clues',
    weak: 'Statistical reference',
  },
  summaryHint: 'The three counts above are directional evidence counts, not an AI probability score.',
  summaryDetail: 'The three counts are directional evidence items only. Items checked but inconclusive are excluded. This is not an "AI probability" score — only red "AI-related" flags are stronger associations.',
  itemStatus: {
    forensicsFound: 'Hint only · reference',
    forensicsNotFound: 'No anomaly hint',
    found: 'Recorded',
    notFound: 'Not found',
  },
  meaning: {
    aiRelevant: 'This item: objective clues related to AI image generation (compare with other items)',
    found: 'This item: recorded — see interpretation notes',
    notFound: 'This item: no clue found',
  },
  report: inspectReport,
} as const
