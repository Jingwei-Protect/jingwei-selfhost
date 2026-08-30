/**
 * Blog posts (zh-Hans).
 *
 * To add a new article:
 * 1. Append a BlogPost to BLOG_POSTS (unique slug + search intent).
 * 2. Mirror copy in en/posts.ts and ja/posts.ts (and zh-Hant if present).
 * 3. Add `blog/<slug>` to frontend/public/seo/routes.json (title, description,
 *    shellHeading, shellParagraphs, jsonLdFile) for all locales.
 * 4. Add the URL to frontend/public/sitemap.xml and SITEMAP_PUBLIC_PATHS.
 * 5. Optional: place Article JSON-LD under frontend/public/seo/.
 */
import { SITE_URL } from '../../../lib/site'
import type { BlogIndexCopy, BlogPost } from '../types'

const G = '/showcase/guide'
const L_PROTECTED = '精卫加水印后'
const L_AI = 'AI 试图修复后'

export const BLOG_CANONICAL = `${SITE_URL}/blog`

export const BLOG_INDEX: BlogIndexCopy = {
  canonical: BLOG_CANONICAL,
  metaTitle: '博客 · 防 AI 洗图与图像归属 | 精卫 Jingwei',
  metaDescription:
    '为什么盗图洗图变容易？五种可见层怎么选？面向画手、设计师、摄影师的完整说明，配合实测矩阵与使用指南。',
  title: '博客',
  lead: '面向创作者的完整说明：署名·快速怎么用、闪卡怎么下载，配合使用指南与实测矩阵阅读。',
}

const C = '/showcase/credit'
const H = '/showcase/holo'

export const BLOG_POSTS: BlogPost[] = [
  {
    slug: 'quick-credit-mode',
    datePublished: '2026-08-29',
    dateModified: '2026-08-29',
    metaTitle: '署名·快速是什么？30秒加水印防AI洗图 | 精卫博客',
    metaDescription:
      '精卫默认「署名·快速」：填创作者姓名即写入可验证 JW 声明，画面自动选浅字符或位移字。适合日常发稿，约30秒，无需注册。',
    intro: {
      kicker: '怎么用',
      title: '署名·快速是什么？30 秒给作品写上可验证身份证',
      lead:
        '署名·快速是精卫 Jingwei（jwprotect.com）的默认保护模式：你填创作者姓名，系统就写入可验证的隐形 JW 声明，并按画面自动选一种浅可见印记。日常发稿大约 30 秒，无需注册，处理完即删。',
      updated: '2026 年 8 月',
    },
    heroMedia: {
      kind: 'compare',
      protectedSrc: `${C}/credit-dog-before.png?v=upload1`,
      aiRestoredSrc: `${C}/credit-dog-after.png?v=upload1`,
      protectedAlt: '小狗插画原图，未加水印',
      aiRestoredAlt: '署名·快速位移字保护后的小狗插画',
      protectedLabel: '原图',
      aiRestoredLabel: '署名·快速 · 位移字',
      caption: '有纹理的画面走轻位移署名。全图几乎看不出差别（只改了约 1% 像素）；请往下看面中放大，Jingwei 在小狗面中。',
    },
    paragraphs: [
      '很多人搜「免费加水印」「防 AI 洗图怎么做」，真正卡住的往往不是参数，而是步骤太多。署名·快速就是为这个场景做的：先把身份证写上，再让可见印记尽量不打扰原图。',
    ],
    sections: [
      {
        heading: '署名·快速是什么？',
        paragraphs: [
          '署名·快速是精卫保护页的默认模式。你填写创作者姓名后，系统会自动打开精卫声明（JW）：把姓名、创作类型和使用限制以机器可读方式写入图像。同时加一层很浅的画面印记，方便肉眼辨认「这张图被保护过」，又不至于像角标那样一眼被 AI 当独立物体抠掉。',
        ],
      },
      {
        heading: '和「手动调节」有什么区别？',
        paragraphs: [
          '署名·快速和手动调节是两套互不共用滑条的模式，不是「自动帮你把手动调一遍」。',
          '署名·快速：填姓名就写 JW；可见印记由系统按画面选浅字符或轻位移（你也可以指定其中一种）；上传 Logo 只打一枚浅淡印。没有铺满位移、浮雕、模糊条、脸部锁这些开关，也不让你逐项改字号、位移像素、Logo 位置和深浅。目标是日常发稿大约 30 秒，画面尽量干净。',
          '手动调节：每一层自己开、自己关、自己调。要 Logo 贴在指定角落、要把位移铺满、要对照实测矩阵叠浮雕或脸部锁，必须改用手动调节。署名·快速里看到的浅字符 / 位移字，是固定淡配方，不是手动页那一套强度滑条。',
        ],
      },
      {
        heading: '怎么用？三步就够',
        paragraphs: [
          '打开保护页，保持默认的「署名·快速」，上传 PNG / JPEG / WebP（iPhone 请先导出 JPG）。填创作者姓名，可选再填画面署名文字或上传 Logo。点「开始保护」，下载 PNG 成品。全程约 30 秒，服务器处理完即删，不经过任何 AI 模型。',
        ],
      },
      {
        heading: '位移字例图：有纹理的小狗',
        paragraphs: [
          '「自动」看到花朵、毛发这类纹理时，通常走轻位移署名（字号约 7%、位移 3 像素、浅阴影，即实验档 c024）。字不是贴上去的色块，而是把原图像素轻轻推歪，形成 Jingwei。红框标出这张例图里印记落在小狗面中的位置。',
        ],
        media: [
          {
            kind: 'compare',
            protectedSrc: `${C}/credit-dog-face-before.png?v=upload1`,
            aiRestoredSrc: `${C}/credit-dog-face-after.png?v=upload1`,
            protectedAlt: '小狗原图面中放大，毛发未被推歪',
            aiRestoredAlt: 'c024 位移字面中放大，毛发被推成 Jingwei',
            protectedLabel: '原图 · 面中放大',
            aiRestoredLabel: 'c024 · 面中放大',
            caption: '这才是实验档小狗签名：字母不是贴在蓝花上的色块，而是把面中毛发轻轻推歪成 Jingwei。',
          },
          {
            kind: 'single',
            src: `${C}/credit-dog-where.png?v=upload1`,
            alt: '小狗位移字凸显图：红框标出面中的 Jingwei',
            caption: '凸显图：红框标出印记落在面中的位置。',
          },
        ],
      },
      {
        heading: '浅字符例图：平坦的猫',
        paragraphs: [
          '插画平涂、大色块背景会走另一条路：满幅很浅的字符/细点，画面中部再加一枚点状浅签名。这是保护页真实浅字符配方打出来的样子，不是手动调节里可以随便拉对比度的半调。',
        ],
        media: [
          {
            kind: 'compare',
            protectedSrc: `${C}/credit-cat-before.png?v=siga1`,
            aiRestoredSrc: `${C}/credit-cat-after.png?v=siga1`,
            protectedAlt: '猫插画原图',
            aiRestoredAlt: '真实浅字符保护后的猫插画',
            protectedLabel: '原图（平坦插画）',
            aiRestoredLabel: '浅字符保护后',
            caption: '远看仍是原画。浅印铺在整张图上，不抢猫和鲨鱼的主体。',
          },
          {
            kind: 'compare',
            protectedSrc: `${C}/credit-cat-zoom-before.png?v=siga1`,
            aiRestoredSrc: `${C}/credit-cat-zoom-after.png?v=siga1`,
            protectedAlt: '猫图面中原图放大，没有浅字符',
            aiRestoredAlt: '猫图面中放大，可见细点与浅字符',
            protectedLabel: '原图 · 面中放大',
            aiRestoredLabel: '保护后 · 面中放大',
            caption: '这是真实浅字符：放大后能看到细小十字和浅点，不是铺满的大号字母。',
          },
          {
            kind: 'single',
            src: `${C}/credit-cat-where.png?v=siga1`,
            alt: '猫浅字符凸显图：红框标出中部点状 Jingwei',
            caption: '凸显图：红框标出点状签名落在面中的位置。框外还有更淡的满幅细点。',
          },
        ],
      },
      {
        heading: '保护之后怎么验证？',
        paragraphs: [
          '把本次下载的 PNG 成品上传到验证页，无需登录。系统会分别报告精卫声明 JW、频域水印、LSB、元数据和追踪锚点是否检出。未检出不等于没处理过；检出则可作为「这张图经过精卫保护」的辅助证据。争议时请保留未经二次压缩的原导出文件。',
        ],
      },
      {
        heading: '什么时候不该只用署名·快速？',
        paragraphs: [
          '如果你要挡针对性的 AI 去水印、换脸或局部重绘，请改用「手动调节」，再叠位移铺满、浮雕、模糊条或脸部浮雕锁，并对照实测矩阵选型。署名·快速优先保证「能验证、不太脏画面」，不是最强防洗图配方。',
          '导出请尽量用 PNG。JPEG 有损压缩可能削弱隐形层。透明通道请不要转 JPEG。',
        ],
      },
    ],
    relatedLinks: [
      { to: '/protect', label: '打开保护页，试用署名·快速' },
      { to: '/verify', label: '验证刚才下的成品' },
      { to: '/blog/jingwei-holo-card', label: '闪卡是什么？怎么下载' },
      { to: '/blog/how-to-use-jingwei-visible-layers', label: '五种可见层怎么选' },
    ],
  },
  {
    slug: 'jingwei-holo-card',
    datePublished: '2026-08-29',
    dateModified: '2026-08-29',
    metaTitle: '闪卡是什么？精卫镭射卡面短视频怎么下载 | 精卫博客',
    metaDescription:
      '精卫闪卡把保护后的作品做成会反光的镭射卡面，可下载约6秒 MP4。指纹状摩尔纹只出现在反光带里，不影响原图颜色。',
    intro: {
      kicker: '新功能',
      title: '闪卡是什么？把保护后的作品做成会反光的镭射卡',
      lead:
        '闪卡是精卫把「保护后的静图」做成一张会随角度反光的镭射卡面，并导出约 6 秒、8 帧/秒的 MP4 短视频。适合发社媒预告、约稿展示。它不是 iPhone 实况照片，也不能代替 PNG 原图去做验证。',
      updated: '2026 年 8 月',
    },
    heroMedia: {
      kind: 'holo',
      cardSrc: `${H}/home-card.jpg?v=credit-faint-2`,
      videoSrc: `${H}/holo-card-demo.mp4`,
      alt: '精卫闪卡成品：悬停可看箔面，下方是导出的短视频',
      caption: '上下两格同一画幅：上面是可悬停的网页闪卡，下面是导出的约 6 秒 MP4。',
    },
    paragraphs: [
      '保护完成之后，保护页可以再「下载闪卡」。文件名跟你的原图走，例如 `cat_holo.mp4`。把这段视频发出去，别人看到的是一张会晃的卡，而不是一张扁平预览图。',
    ],
    sections: [
      {
        heading: '闪卡是什么？和普通水印图有什么区别？',
        paragraphs: [
          '闪卡是保护后作品的展示层，不是新的水印算法。静图上的 JW 声明、位移或浅字符已经写进像素；闪卡只是用卡面箔层（虹彩扫光 + 同向细密摩尔纹 + 细闪）把这张图「装进」一张会反光的卡里。不反光时你看到的是清晰整图，原图颜色不被整卡染色。',
        ],
      },
      {
        heading: '怎么下载闪卡？',
        paragraphs: [
          '先按署名·快速或手动调节完成保护并下载 PNG。在结果区点「下载闪卡」，等待录制（本机需安装 Chrome；服务器端由站点完成）。下载得到约 6 秒的 MP4，可直接发微博、小红书、X 或 Discord。悬停网页上的样卡也能预览箔面，不必先导出。',
        ],
      },
      {
        heading: '卡面上到底有什么？',
        paragraphs: [
          '三件事叠在反光带里：一条青—金—粉的虹彩扫光；同方向、亚像素间距的细密光栅，干涉后像指纹脊线；以及稀疏的亮点细闪。纹路被裁在反光带内，带外透明，所以「只有反光的地方看得到指纹」。银边是卡框，不是灰黑边。看上面的成品卡和短视频即可，不必再对静帧。',
        ],
      },
      {
        heading: '闪卡适合发到哪里？不能当什么用？',
        paragraphs: [
          '适合当预告、作品卡面、约稿展示。不适合当唯一存档：验证请上传 PNG 成品，不要上传闪卡视频截图。平台再压一次码率，箔面细节会变糊，这是视频传播的正常损耗，不是保护失败。',
        ],
      },
    ],
    relatedLinks: [
      { to: '/protect', label: '保护作品并下载闪卡' },
      { to: '/blog/quick-credit-mode', label: '先看署名·快速怎么用' },
      { to: '/guide/watermark-matrix', label: '各层 vs AI 洗图实测' },
    ],
  },
  {
    slug: 'why-ai-image-theft-is-easy',
    datePublished: '2026-07-05',
    dateModified: '2026-07-06',
    metaTitle: '如何让你的水印扛过 AI 洗图？ | 精卫博客',
    metaDescription:
      '角标和大字水印为什么拦不住 AI？洗图在做什么？精卫可见防盗层与隐形归属层如何配合，附使用指南实测对比图。',
    intro: {
      kicker: '创作者必读',
      title: '如何让你的水印扛过 AI 洗图？',
      lead: '',
      updated: '2026 年 7 月',
    },
    heroMedia: {
      kind: 'compare',
      protectedSrc: `${G}/disp-repeat-protected.png`,
      aiRestoredSrc: `${G}/disp-repeat-ai-restored.png`,
      protectedAlt: '位移水印铺满重复，精卫加水印后',
      aiRestoredAlt: '位移水印铺满重复，AI 试图修复后',
      protectedLabel: L_PROTECTED,
      aiRestoredLabel: L_AI,
      caption: '位移水印 · 铺满重复：AI 试图抹除署名后，红框处仍留涂抹与色块。',
    },
    paragraphs: [
      '很多创作者都遇到过：明明加了水印，但别人轻易就去掉了并拿去自用。过去要靠 PS 一点点盖，还要懂通道和蒙版这些门道，学习成本不低。现在把图丢进 AI 工具，往往一条指令、几秒钟就能抹掉再补上。',
      '问题不在于「有没有加水印」，而在于水印是不是仍按老思路在做：贴上去、规矩、清晰、和画面分家。AI 洗图正是利用这些弱点。',
    ],
    sections: [
      {
        heading: '为什么老水印不顶用了',
        paragraphs: [
          '太规矩、太统一：角标、版权声明条、重复小 logo，位置和样式都固定。AI 见多了，就像拿到说明书，批量识别、批量抹除并不难。',
          '太清晰、与画面分离：水印为了让人看见，常和底下内容分得很开。AI 把它当成独立物体抠掉，再专门修复空出来的区域，反而更省事。',
          '信息量少、易被重建：几个字母或一个小图标，像素信息不多。抹掉以后，AI 按周围纹理和颜色趋势去填，看起来就像本来就没有水印。',
        ],
      },
      {
        heading: '洗图，就是 AI 在「修复」你的作品',
        paragraphs: [
          '洗图的核心是 inpainting：把不想要的区域涂掉，再根据周围画面智能生成内容。常见做法包括局部清除（角标、大字）、整图微调重绘（铺满水印）、裁边再扩（边缘水印）。',
          '上面头图就是「铺满重复」位移水印的实测：左为精卫加水印后，右为 AI 试图修复后。红框标出的不是无痕还原，而是抹不平的破绽。',
        ],
      },
      {
        heading: '精卫的办法：两层防护',
        paragraphs: [
          '可见防盗层会在画面里做微观改造，让改动和像素结构长在一起。AI 强行处理时，容易扭曲、模糊或留下噪点，洗图的人一看就知道动过手脚。浮雕纹理、模糊条、脸部浮雕锁等各有实测，用法和选型见下一篇博客与实测矩阵。',
          '隐形归属层写入 JW 声明和频域水印，像秘密印记。截图、压缩后仍可能保留部分信息，验证页可读，便于申诉。若主要担心「拿走干净原图」，可见层不要省；若主要担心「证明是我的」，JW 与频域不要省。',
        ],
        media: [
          {
            kind: 'compare',
            protectedSrc: `${G}/emboss-protected.png`,
            aiRestoredSrc: `${G}/emboss-ai-restored.png`,
            protectedAlt: '浮雕纹理，精卫加水印后',
            aiRestoredAlt: '浮雕纹理，AI 试图修复后',
            protectedLabel: L_PROTECTED,
            aiRestoredLabel: L_AI,
            caption: '浮雕纹理：全图轻微斜线纹，AI 抹平后易留修复破绽。',
          },
        ],
      },
    ],
    relatedLinks: [
      { to: '/guide/watermark-matrix', label: '查看实测矩阵' },
      { to: '/blog/how-to-use-jingwei-visible-layers', label: '五种可见层怎么选' },
      { to: '/protect', label: '开始保护作品' },
    ],
  },
  {
    slug: 'how-to-use-jingwei-visible-layers',
    datePublished: '2026-07-05',
    dateModified: '2026-08-28',
    metaTitle: '精卫怎么用：五种可见层怎么选 | 精卫博客',
    metaDescription:
      '位移、半调、浮雕、模糊条、脸部浮雕锁：用法、适合场景、与 JW 隐形层如何叠加。使用指南实测对比。',
    intro: {
      kicker: '使用指南',
      title: '精卫怎么用：五种可见层怎么选',
      lead:
        '发图前别只贴角标。精卫一般是两层：可见层挡洗图，隐形层留归属。下面每种效果都配使用指南里的实测对比图。',
      updated: '2026 年 7 月',
    },
    heroMedia: {
      kind: 'compare',
      protectedSrc: `${G}/disp-tile-protected.png`,
      aiRestoredSrc: `${G}/disp-tile-ai-restored.png`,
      protectedAlt: '位移水印集中整词，精卫加水印后',
      aiRestoredAlt: '位移水印集中整词，AI 试图修复后',
      protectedLabel: L_PROTECTED,
      aiRestoredLabel: L_AI,
      caption: '位移水印 · 集中整词',
    },
    paragraphs: [
      '打开保护页上传作品，默认用署名·快速；要自己配层就改手动调节。预览区拖动虚线框摆位置，生成预览，橡皮擦精修，满意后导出。全程约半分钟，处理完即删。',
    ],
    sections: [
      {
        heading: '位移水印',
        paragraphs: [
          '把署名区域的像素轻微推歪，与画面长在一起。三种排列：集中整词、随机分散、铺满重复。署名最好落在主体轮廓或边缘。',
        ],
        media: [
          {
            kind: 'compare',
            protectedSrc: `${G}/disp-tile-protected.png`,
            aiRestoredSrc: `${G}/disp-tile-ai-restored.png`,
            protectedAlt: '位移水印集中整词',
            aiRestoredAlt: '位移水印集中整词，AI 试图修复后',
            protectedLabel: L_PROTECTED,
            aiRestoredLabel: L_AI,
            caption: '集中整词',
          },
          {
            kind: 'compare',
            protectedSrc: `${G}/disp-scatter-protected.png`,
            aiRestoredSrc: `${G}/disp-scatter-ai-restored.png`,
            protectedAlt: '位移水印随机分散',
            aiRestoredAlt: '位移水印随机分散，AI 试图修复后',
            protectedLabel: L_PROTECTED,
            aiRestoredLabel: L_AI,
            caption: '随机分散',
          },
        ],
      },
      {
        heading: '半调网点与 ASCII 字符',
        paragraphs: [
          '半调把细颗粒压进背景高频；ASCII 用字符纹理铺满画面。两者正常观看可接受，AI 平坦化后常留块面或断裂。',
        ],
        media: [
          {
            kind: 'compare',
            protectedSrc: `${G}/halftone-protected.png`,
            aiRestoredSrc: `${G}/halftone-ai-restored.png`,
            protectedAlt: '半调网点',
            aiRestoredAlt: '半调网点，AI 试图修复后',
            protectedLabel: L_PROTECTED,
            aiRestoredLabel: L_AI,
            caption: '半调网点',
          },
          {
            kind: 'compare',
            protectedSrc: `${G}/moire-protected.png`,
            aiRestoredSrc: `${G}/moire-ai-restored.png`,
            protectedAlt: 'ASCII 字符可见层',
            aiRestoredAlt: 'ASCII，AI 试图修复后',
            protectedLabel: L_PROTECTED,
            aiRestoredLabel: L_AI,
            caption: 'ASCII 字符',
          },
        ],
      },
      {
        heading: '浮雕纹理',
        paragraphs: [
          '全图施加轻微立体斜线纹，改变边缘与肌理。不太适合极简平涂，更适合插画、摄影、角色立绘。',
        ],
        media: [
          {
            kind: 'compare',
            protectedSrc: `${G}/emboss-protected.png`,
            aiRestoredSrc: `${G}/emboss-ai-restored.png`,
            protectedAlt: '浮雕纹理',
            aiRestoredAlt: '浮雕纹理，AI 试图修复后',
            protectedLabel: L_PROTECTED,
            aiRestoredLabel: L_AI,
            caption: '浮雕纹理',
          },
        ],
      },
      {
        heading: '模糊条与模糊块',
        paragraphs: [
          '模糊条是横向半透明带，适合交付预览和挡住关键信息。下图是模糊条实测。',
          '模糊块是画笔涂抹的色块，和「一条模糊带」不是同一层。脸部浮雕锁请在保护页用手动调节预览。',
        ],
        media: [
          {
            kind: 'compare',
            protectedSrc: `${G}/ascii-protected.png`,
            aiRestoredSrc: `${G}/ascii-ai-restored.png`,
            protectedAlt: '模糊条',
            aiRestoredAlt: '模糊条，AI 试图修复后',
            protectedLabel: L_PROTECTED,
            aiRestoredLabel: L_AI,
            caption: '模糊条',
          },
          {
            kind: 'compare',
            protectedSrc: `${G}/dots-protected.png`,
            aiRestoredSrc: `${G}/dots-ai-restored.png`,
            protectedAlt: '模糊块',
            aiRestoredAlt: '模糊块，AI 试图修复后',
            protectedLabel: L_PROTECTED,
            aiRestoredLabel: L_AI,
            caption: '模糊块',
          },
        ],
      },
      {
        heading: '怎么叠',
        paragraphs: [
          '常用：位移或半调，再加 JW 声明与频域水印。低调方案：隐形层加追踪锚点。',
          '完整对比见实测矩阵页。第一篇博客讲「为什么 AI 洗图容易」，这篇讲「怎么选层」。',
        ],
      },
    ],
    relatedLinks: [
      { to: '/guide/watermark-matrix', label: '9 组实测矩阵' },
      { to: '/protect', label: '打开保护页' },
      { to: '/verify', label: '验证水印' },
    ],
  },
]

export function getBlogPost(slug: string): BlogPost | undefined {
  const id = BLOG_SLUG_ALIASES[slug] ?? slug
  return BLOG_POSTS.find(p => p.slug === id)
}

export function postCanonical(slug: string): string {
  return `${SITE_URL}/blog/${slug}`
}

/** 旧 slug 兼容 */
export const BLOG_SLUG_ALIASES: Record<string, string> = {
  'how-jingwei-visible-layers-work': 'how-to-use-jingwei-visible-layers',
}
