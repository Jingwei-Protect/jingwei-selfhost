/**

 * Author's letter — /about SEO page (English bundle)

 */



import { CONTACT_EMAIL, SITE_NAME, SITE_URL } from '../../lib/site'



export const AUTHOR_LETTER_CANONICAL = `${SITE_URL}/about`



export const AUTHOR_LETTER_META_TITLE = `Author\'s Note · Why ${SITE_NAME} Exists | The Aura of Art & Creation`



export const AUTHOR_LETTER_META_DESCRIPTION =

  'A letter on why Jingwei exists: Walter Benjamin\'s aura of art, the AI-era crisis of trust, saving human traces in images, and the meaning of throwing one stone.'



export const AUTHOR_LETTER_DATE_PUBLISHED = '2026-06-01'

export const AUTHOR_LETTER_DATE_MODIFIED = '2026-06-14'



export const AUTHOR_LETTER_INTRO = {

  kicker: 'Author\'s Note',

  title: 'A Letter to Creators',

  lead: `For anyone who lands here. This is not a product manual. It is why I built ${SITE_NAME}.`,

  updated: 'June 2026',

}



export const AUTHOR_LETTER_PARAGRAPHS: readonly string[] = [

  'Ten years ago, when I took fragmented information, film, and photography for granted, I did not truly understand Benjamin from a century ago. I did not understand what he described: that a work of art belongs to a particular moment, a particular place, an original - an aura that is hard to name yet real. Nor did I truly worry about what happens to that aura when a work can be reproduced endlessly, almost without loss, and how it might fade bit by bit.',

  'Then I was kicked headlong into this AI-era crisis of trust.',

  'Countless works spread without end - cropped, compressed, reposted, and uploaded again and again. What unsettled me most was how easily creators are erased in that process. The work keeps moving, but its tie to the author grows thinner. In the end, even the person is stripped away, leaving only styles, surfaces, and results that can be called up.',

  'In this new age where copying costs almost nothing, inside information that multiplies without limit, everyone questions how much "living human presence" remains in any piece of information - and then competes to make things that look more human while carrying no trace of any actual person.',

  'Painting seems to feel the shock earliest in every era, and the AI era is no different. But perhaps answers also grow from it first. When photography appeared, people thought painting would be replaced. When mechanical printing and the internet changed how works travel, others feared art would be diluted by endlessly reproducible media. Art did not end because of that. On the contrary, after every shock it moves closer to a deeper question: where does that aura come from - the thing that cannot be copied and cannot be replaced by the form of transmission?',

  'As someone who does not draw especially well, whenever I want to begin now I ask myself: if AI can generate a more accurate, more polished image in one second, why should I still start? That hesitation unsettles me most. What frightens me most in this crisis of trust is whether we still believe that a slow, imperfect, even hesitant creative process still means something in itself.',

  'If in the past we tried to preserve the aura of the artwork, then today what may be harder is preserving the aura of the person. I think a person\'s aura may come from the traces left in hesitation, choice, persistence, revision, and starting over - from the impulse to begin even knowing the result can be replaced in an instant. Jingwei appeared in that context. It is not here to stop technology, nor to reject the future. It only wants works, as they move through circulation, to still carry this information: "this was made by a specific human, and this is how that person hopes it will be treated." Even if that preservation is imperfect, even if it only leaves one more faint but clear trace, I still think it is worth doing.',

  'Many rules that look natural today began as the persistence of a few people, and only later became language everyone shares. Copyright was like that. CC markers were like that. So were all efforts around attribution, permission, and boundaries.',

  'Jingwei knows the sea cannot be filled, yet still carries stones and drops them into the waves. Sisyphus knows the boulder will roll down again, yet still pushes it up the mountain. God made the Tower of Babel and scattered languages and directions - yet in different corners of the world, in different times, people keep doing similar things. Not because they can reach the same outcome, but because in different places they make similar choices. To me, that is our clumsy human heroism. And that is a moment when human stars shine.',

  'And Jingwei is my stone.',

]



export const AUTHOR_LETTER_CTA = {

  title: 'If you want to throw a stone too',

  links: [

    { to: '/protect', label: 'Protect your work' },

    { to: '/protocol', label: 'Read the JW declaration' },

    { to: '/faq', label: 'FAQ' },

  ] as const,

  contact: `Questions? Email ${CONTACT_EMAIL}`,

}



export function buildAuthorLetterJsonLd(): Record<string, unknown> {

  const body = AUTHOR_LETTER_PARAGRAPHS.join('\n\n')

  return {

    '@context': 'https://schema.org',

    '@type': 'Article',

    headline: AUTHOR_LETTER_INTRO.title,

    description: AUTHOR_LETTER_META_DESCRIPTION,

    url: AUTHOR_LETTER_CANONICAL,

    inLanguage: 'en',

    datePublished: AUTHOR_LETTER_DATE_PUBLISHED,

    dateModified: AUTHOR_LETTER_DATE_MODIFIED,

    author: {

      '@type': 'Organization',

      name: SITE_NAME,

      url: SITE_URL,

    },

    publisher: {

      '@type': 'Organization',

      name: SITE_NAME,

      url: SITE_URL,

    },

    articleBody: body,

    about: [

      'image attribution',

      'creators in the AI era',

      'aura of art',

      'Walter Benjamin',

      'Jingwei Declaration',

      'Creative Commons',

    ],

  }

}


