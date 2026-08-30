export const inspectReport = {
  disclaimer:
    'This page is an analysis report listing objective findings we can read from the file. '
    + 'It cannot make a final call between human-made and AI-generated. '
    + 'A missing item does not prove the opposite—for example, missing attribution or camera metadata '
    + 'is common on images downloaded from social platforms. Review multiple clues together and decide yourself.',
  categories: {
    provenance: 'Provenance credentials',
    structure: 'File structure',
    forensics: 'Pixel forensics',
  },
  strengthBadge: {
    shellRecord: 'Container shell',
  },
  hints: {
    lowNoise:
      'Low noise residual: the image is relatively smooth. Some AI outputs show this, but flat color and blur can too (reference only).',
    highPeak:
      'Strong periodic spectral peaks: may come from upsampling grids or repeated texture. Not conclusive alone (reference only).',
  },
  clues: {
    embeddedThumbnail: 'Embedded preview thumbnail (common in camera/editor exports)',
    adobeMarker: 'Adobe (APP14) segment present—likely processed with Adobe software',
    appSegments: 'APP segments: {apps}',
    colorManagement: 'Color management chunks: {chunks}',
    noColorManagement: 'No color management chunks (sometimes seen in bare AI PNG exports)',
  },
  items: {
    ai_metadata: {
      title: 'AI tool metadata',
      variants: {
        found: {
          status: 'AI-related',
          meaning: 'This item: self-reported AI tool metadata detected ({tools})—strong AI association',
          interpretation:
            'Parameters/workflow fields left by the tool are effectively a self-declaration of AI generation. '
            + 'If not stripped by a platform, this is among the strongest direct evidence—still combine with C2PA and other items.',
          note: 'The file contains AI-generation tool metadata—a strong self-reported signal. Metadata can be removed manually; presence ≠ sole source.',
        },
        not_found: {
          status: 'Not found',
          meaning: 'This item: no AI tool metadata (may have been removed or stripped by a platform)',
          interpretation:
            'Missing A1111/ComfyUI-style fields does not prove “not AI”—very common after re-save or screenshot.',
          note: 'No AI tool metadata found. Social platforms and re-saves often strip this; not found ≠ human-made.',
        },
      },
    },
    c2pa: {
      title: 'C2PA content credentials',
      variants: {
        unavailable: {
          status: 'Not checked',
          meaning: 'This item: C2PA could not be read in this environment—skipped',
          interpretation: 'This environment cannot read C2PA; this item was skipped.',
          note: 'C2PA reader library not available in this environment.',
        },
        not_found: {
          status: 'Not found',
          meaning: 'This item: no C2PA credentials (common after screenshot/platform download)',
          interpretation: 'No cryptographic provenance chain—cannot infer AI from absence; many AI images lose C2PA after re-save.',
          note: 'No C2PA Content Credentials detected. Screenshots, re-encodes, and platforms often remove signatures—no signature ≠ AI.',
        },
        ai_declared: {
          status: 'AI-related',
          meaning: 'This item: C2PA declares algorithm/AI generation (hard evidence)',
          interpretation:
            'See digital_source_type / claim_generator in JSON. '
            + 'This is the publisher’s self-declaration in the credential—strong AI association; combine with other items.',
          note: 'C2PA credentials declare algorithm/AI generation (provenance claim, not pixel analysis).',
        },
        ai_doubtful: {
          status: 'Claim doubtful',
          meaning: 'This item: C2PA mentions AI but signature verification failed—evidence uncertain',
          interpretation: 'AI-related fields present but signature unavailable—may be damaged or tampered; not reliable AI proof.',
          note: 'C2PA contains AI-related claims but signature failed or is unavailable—use with caution.',
        },
        has_chain: {
          status: 'Has credentials',
          meaning: 'This item: C2PA provenance chain present; no algorithm/AI declaration',
          interpretation:
            'Edit/publish workflow may be traceable—more compliance/pro workflow. No AI declaration does not prove “not AI”.',
          note: 'C2PA credentials detected with traceable source/edit chain. See signature_valid for signature status.',
        },
      },
    },
    exif_camera: {
      title: 'Camera EXIF capture chain',
      variants: {
        found: {
          status: 'Photo-like',
          meaning: 'This item: full camera/capture parameters—more like a photographed workflow, unlike typical bare AI export',
          interpretation:
            'Complete Make/Model/exposure fields lean toward human capture. '
            + 'With no AI metadata, strengthens “not bare AI export”—but EXIF can be forged.',
          note: 'A coherent camera capture parameter chain is a strong photo-source signal (can be forged—use holistically).',
        },
        partial: {
          status: 'Indeterminate',
          meaning: 'This item: partial metadata only—not enough for a full camera chain; source undetermined',
          interpretation:
            'Incomplete fields cannot infer AI export or platform image, nor prove human creation. Combine with other evidence.',
          note:
            'Could not read a full camera EXIF chain—cannot determine human art, digital painting, or AI. '
            + 'Missing metadata after PNG export, editing, or platform download is very common and not directional.',
        },
        none: {
          status: 'Indeterminate',
          meaning: 'This item: no camera capture chain metadata; source undetermined',
          interpretation:
            'No camera EXIF is common after digital art export, screenshots, compression, and platform downloads—'
            + 'cannot infer AI or human; combine with other evidence.',
          note:
            'Could not read a full camera EXIF chain—cannot determine human art, digital painting, or AI. '
            + 'Missing metadata after PNG export, editing, or platform download is very common and not directional.',
        },
      },
    },
    file_structure: {
      title: 'File structure fingerprint',
      variants: {
        read_error: {
          status: 'Not found',
          meaning: 'This item: could not read file structure',
          interpretation: 'File structure check failed—use other items.',
          note: 'Could not read file structure.',
        },
        no_clues: {
          status: 'Structural compare',
          meaning: 'This item: plain container—no extra traces typical of AI export or camera/editor pipeline',
          interpretation:
            'Structure alone shows no clear bias. If AI metadata and C2PA above are not red, '
            + 'there is currently no hard AI-generation evidence.',
          note:
            'File structure is for comparison only—platform re-encode changes containers; '
            + 'not a substitute for AI metadata/C2PA. Shell-only hits do not count in the structural clue tally.',
        },
        has_thumbnail: {
          status: 'Structural compare',
          meaning: 'This item: embedded preview thumbnail—more like camera/editor export than typical AI bare export',
          interpretation:
            'Structure aligns with photo/edit workflow. Without AI metadata and C2PA claims, leans away from bare AI export—still check other items.',
          note:
            'File structure is for comparison only—platform re-encode changes containers; '
            + 'not a substitute for AI metadata/C2PA. Shell-only hits do not count in the structural clue tally.',
        },
        no_color_png: {
          status: 'Structural compare',
          meaning: 'This item: missing color management chunks—sometimes seen in bare AI PNG exports',
          interpretation:
            'Many tools save PNG without gAMA/sRGB/iCCP; human design exports can too. '
            + 'Cannot conclude alone—if nothing is red above, this item alone is not enough.',
          note:
            'File structure is for comparison only—platform re-encode changes containers; '
            + 'not a substitute for AI metadata/C2PA. Shell-only hits do not count in the structural clue tally.',
        },
        has_color_png: {
          status: 'Structural compare',
          meaning: 'This item: color management chunks present—closer to regular design/editor export than typical bare AI PNG',
          interpretation:
            'Structure suggests a professional export path. Without AI metadata and C2PA, less like typical bare AI export.',
          note:
            'File structure is for comparison only—platform re-encode changes containers; '
            + 'not a substitute for AI metadata/C2PA. Shell-only hits do not count in the structural clue tally.',
        },
        adobe: {
          status: 'Structural compare',
          meaning: 'This item: Adobe processing segment—more like post-edit pipeline shell trace',
          interpretation: 'May have passed through Adobe software—structure alone cannot judge AI; rely on hard evidence.',
          note:
            'File structure is for comparison only—platform re-encode changes containers; '
            + 'not a substitute for AI metadata/C2PA. Shell-only hits do not count in the structural clue tally.',
        },
        app_shell: {
          status: 'Shell only',
          meaning: 'This item: JPEG container detected ({apps})—no typical AI bare-export structure',
          interpretation:
            'Only means Exif/IPTC-style metadata containers remain—not AI self-report or C2PA. '
            + 'If nothing is red above, treat as: shell present, no AI structural side evidence.',
          note:
            'File structure is for comparison only—platform re-encode changes containers; '
            + 'not a substitute for AI metadata/C2PA. Shell-only hits do not count in the structural clue tally.',
        },
        generic: {
          status: 'Structural compare',
          meaning: 'This item: structural traces recorded—judge with hard evidence',
          interpretation: 'See JSON. Platforms rewrite structure—prioritize whether AI metadata/C2PA are flagged red above.',
          note:
            'File structure is for comparison only—platform re-encode changes containers; '
            + 'not a substitute for AI metadata/C2PA. Shell-only hits do not count in the structural clue tally.',
        },
      },
    },
    pixel_forensics: {
      title: 'Pixel forensics (reference only)',
      variants: {
        error: {
          status: 'No anomaly hint',
          meaning: 'This item: pixel forensics unavailable',
          interpretation: 'Pixel statistics check failed—use other items.',
          note: 'Pixel forensics unavailable.',
        },
        anomaly: {
          status: 'Hint only · reference',
          meaning: 'This item: pixel stats raised hints worth a manual look—cannot conclude alone',
          interpretation:
            'Numbers and hints below describe statistical shape—hand-drawn, photo, compression, and screenshots can mislead. '
            + 'Must combine with provenance, metadata, and human judgment—cannot label AI alone.',
          note:
            'Pixel stats are the weakest signal—unreliable across unknown models and after compression, high false positives. '
            + 'Shows measurements and “worth reviewing” hints only—not a standalone verdict.',
        },
        normal: {
          status: 'No anomaly hint',
          meaning: 'This item: no obvious anomaly hints in pixel stats—does not prove human-made',
          interpretation:
            'Raw numbers below describe texture statistics. '
            + 'No hints does not mean “not AI”—compression, unknown models, and art style can hide traces.',
          note:
            'Pixel stats are the weakest signal—unreliable across unknown models and after compression, high false positives. '
            + 'Shows measurements and “worth reviewing” hints only—not a standalone verdict.',
        },
      },
    },
  },
} as const
