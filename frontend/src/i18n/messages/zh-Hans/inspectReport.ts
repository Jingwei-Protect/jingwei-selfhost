export const inspectReport = {
  disclaimer:
    '本页给出的是分析报告，只列出我们在文件里查到的客观发现，'
    + '不能替你在「人画 / AI 画」之间做最终认定。'
    + '某一项查不到，也不代表相反结论。比如没有署名信息、没有相机信息，'
    + '在社交平台下载的图里很常见。请你把多项线索一起看，再自己判断。',
  categories: {
    provenance: '来源凭证',
    structure: '文件结构',
    forensics: '像素取证',
  },
  strengthBadge: {
    shellRecord: '外壳记录',
  },
  hints: {
    lowNoise: '噪声残差偏低：画面较平滑，部分 AI 生成图会出现，但纯色块、模糊图也会（仅参考）',
    highPeak: '频谱周期性峰值较强：可能来自上采样网格或重复纹理，不能单独下结论（仅参考）',
  },
  clues: {
    embeddedThumbnail: '含嵌入缩略图（常见于相机/编辑器导出）',
    adobeMarker: '含 Adobe(APP14) 段，疑似经 Adobe 系软件处理',
    appSegments: 'APP 段：{apps}',
    colorManagement: '含色彩管理块：{chunks}',
    noColorManagement: '无色彩管理块（部分 AI 直出 PNG 的特征之一）',
  },
  items: {
    ai_metadata: {
      title: 'AI 生成工具元数据',
      variants: {
        found: {
          status: '与 AI 相关',
          meaning: '本项：检出 AI 工具自报元数据（{tools}），与 AI 生图关联强',
          interpretation:
            '工具在文件内留下的参数/工作流字段，相当于作者自报使用 AI 生成。'
            + '若未被平台剥离，这是最直接的硬证据之一；请仍结合 C2PA 等综合判断。',
          note: '图像文件自带 AI 生成工具元数据，属强信号（工具自报）。元数据可被手动清除，存在≠唯一来源。',
        },
        not_found: {
          status: '未发现',
          meaning: '本项：未见 AI 工具元数据（可能已被人为清除或平台剥离）',
          interpretation:
            '没有 A1111/ComfyUI 等字段，不能据此认定「非 AI」——转存、截图后很常见。',
          note: '未发现 AI 工具元数据。注意：社交平台与二次保存通常会剥离此类信息，未发现≠人类创作。',
        },
      },
    },
    c2pa: {
      title: 'C2PA 内容凭证',
      variants: {
        unavailable: {
          status: '未检测',
          meaning: '本项：环境无法读取 C2PA，已跳过',
          interpretation: '本环境无法读取 C2PA，此项跳过。',
          note: '运行环境未安装 c2pa 读取库，无法核验 C2PA。',
        },
        not_found: {
          status: '未发现',
          meaning: '本项：无 C2PA 凭证（截图/平台下载后很常见）',
          interpretation: '无密码学来源链，不能据此认定是 AI；许多 AI 图转存后也会丢失 C2PA。',
          note: '未检测到 C2PA Content Credentials。注意：截图/转存/平台重编码会清除签名，无签名≠AI。',
        },
        ai_declared: {
          status: '与 AI 相关',
          meaning: '本项：C2PA 声明内容与算法/AI 生成相关（硬证据）',
          interpretation:
            '见 JSON 中 digital_source_type / claim_generator。'
            + '这是发布方在凭证中的自报，与 AI 直接生图关联强；请结合其他项综合判断。',
          note: 'C2PA 凭证显示该内容声明为算法/AI 生成（来源声明，非像素判定）。',
        },
        ai_doubtful: {
          status: '声明存疑',
          meaning: '本项：C2PA 含 AI 声明但验签未通过，证据存疑',
          interpretation: '出现算法/AI 类字段但签名不可用，可能损坏或被篡改，不能当作可靠 AI 凭证。',
          note: 'C2PA 含 AI 相关声明，但签名未通过或不可用，请谨慎采信。',
        },
        has_chain: {
          status: '有凭证',
          meaning: '本项：有 C2PA 来源链，未声明算法/AI 生成',
          interpretation:
            '可追溯编辑/发布流程，更偏合规或专业链路；未声明 AI，不等于证明「非 AI」。',
          note: '检测到 C2PA 凭证，可追溯来源/编辑链。签名有效性见 signature_valid。',
        },
      },
    },
    exif_camera: {
      title: '相机 EXIF 拍摄链',
      variants: {
        found: {
          status: '偏实拍',
          meaning: '本项：见完整相机/拍摄参数，更像实拍流程，与 AI 直出常见形态不一致',
          interpretation:
            'Make/Model/曝光等字段齐全时，整体更偏人类拍摄来源；'
            + '若同时无 AI 元数据，可加强「非 AI 直出」判断，但 EXIF 仍可伪造。',
          note: '存在较完整的相机拍摄参数链，是较强的实拍来源信号（仍可被伪造，仅供综合判断）。',
        },
        partial: {
          status: '无法判定',
          meaning: '本项：读到部分元数据，但不足以构成完整相机拍摄链，无法判定来源',
          interpretation:
            '仅有个别字段或信息不完整时，不能推断为 AI 直出或平台图；'
            + '亦不能反推为「人类创作」。请结合其他证据综合判断。',
          note:
            '未能读取完整相机 EXIF 拍摄链，无法据此判定是人类创作、数字绘画还是 AI 生成。'
            + '画师导出 PNG、后期编辑、平台转存后元数据缺失极为常见，不构成任何指向性结论。',
        },
        none: {
          status: '无法判定',
          meaning: '本项：未能读取相机拍摄链元数据，无法判定来源',
          interpretation:
            '无相机 EXIF 在数字绘画导出、截图、压缩与平台下载后都很常见，'
            + '不能据此认定 AI，也不能据此认定人类创作；请结合其他证据或人工判断。',
          note:
            '未能读取完整相机 EXIF 拍摄链，无法据此判定是人类创作、数字绘画还是 AI 生成。'
            + '画师导出 PNG、后期编辑、平台转存后元数据缺失极为常见，不构成任何指向性结论。',
        },
      },
    },
    file_structure: {
      title: '文件结构指纹',
      variants: {
        read_error: {
          status: '未发现',
          meaning: '本项：无法读取文件结构',
          interpretation: '文件结构检测失败，请结合其他项判断。',
          note: '无法读取文件结构。',
        },
        no_clues: {
          status: '结构对照',
          meaning: '本项：文件外壳较素，未见典型 AI 直出或相机/编辑器导出的额外结构痕迹',
          interpretation:
            '单凭结构看不出明显偏向。若上方「AI 工具元数据」「C2PA」也无红色提示，'
            + '则目前缺少与 AI 生图相关的硬证据。',
          note:
            '文件结构仅供对照：平台重编码会改写容器，不能替代 AI 元数据/C2PA 硬证据。'
            + '仅检测到外壳时，不计入上方「结构线索」计数。',
        },
        has_thumbnail: {
          status: '结构对照',
          meaning: '本项：含嵌入预览图，更像相机/编辑器导出，不太像常见 AI 直出结构',
          interpretation:
            '结构形态与实拍/后期编辑流程更一致。若同时无 AI 元数据与 C2PA 声明，'
            + '整体更偏向非 AI 直出，但仍需结合其他项。',
          note:
            '文件结构仅供对照：平台重编码会改写容器，不能替代 AI 元数据/C2PA 硬证据。'
            + '仅检测到外壳时，不计入上方「结构线索」计数。',
        },
        no_color_png: {
          status: '结构对照',
          meaning: '本项：缺少色彩管理块，AI 直出 PNG 较常呈现类似特征',
          interpretation:
            '不少绘图工具直存 PNG 会缺少 gAMA/sRGB/iCCP；人类设计导出也可能如此。'
            + '结构对照不能单独定性——若上方无红色「与 AI 相关」，仅凭此项不能下结论。',
          note:
            '文件结构仅供对照：平台重编码会改写容器，不能替代 AI 元数据/C2PA 硬证据。'
            + '仅检测到外壳时，不计入上方「结构线索」计数。',
        },
        has_color_png: {
          status: '结构对照',
          meaning: '本项：含色彩管理块，更接近常规设计/编辑器导出，与常见 AI 直存 PNG 不太像',
          interpretation:
            '结构形态更偏专业导出流程。若仍无 AI 元数据与 C2PA 声明，整体不太像典型 AI 直出。',
          note:
            '文件结构仅供对照：平台重编码会改写容器，不能替代 AI 元数据/C2PA 硬证据。'
            + '仅检测到外壳时，不计入上方「结构线索」计数。',
        },
        adobe: {
          status: '结构对照',
          meaning: '本项：见 Adobe 处理段，更像后期编辑流程的外壳痕迹',
          interpretation: '说明可能经 Adobe 系软件处理；单凭结构不能判断是否 AI 生成，请以硬证据为准。',
          note:
            '文件结构仅供对照：平台重编码会改写容器，不能替代 AI 元数据/C2PA 硬证据。'
            + '仅检测到外壳时，不计入上方「结构线索」计数。',
        },
        app_shell: {
          status: '仅外壳',
          meaning: '本项：检测到 JPEG 外壳（{apps}），未见典型 AI 直出结构特征',
          interpretation:
            '仅说明文件仍带 Exif/IPTC 等元数据容器，并非 AI 工具自报或 C2PA 声明。'
            + '若上方无红色「与 AI 相关」，在此项上视为：有外壳、无 AI 结构侧证。',
          note:
            '文件结构仅供对照：平台重编码会改写容器，不能替代 AI 元数据/C2PA 硬证据。'
            + '仅检测到外壳时，不计入上方「结构线索」计数。',
        },
        generic: {
          status: '结构对照',
          meaning: '本项：记录到结构痕迹，需结合硬证据判断',
          interpretation: '详见 JSON。平台转存会改写结构，请以上方 AI 元数据、C2PA 是否标红为准。',
          note:
            '文件结构仅供对照：平台重编码会改写容器，不能替代 AI 元数据/C2PA 硬证据。'
            + '仅检测到外壳时，不计入上方「结构线索」计数。',
        },
      },
    },
    pixel_forensics: {
      title: '像素取证（仅参考）',
      variants: {
        error: {
          status: '无异常提示',
          meaning: '本项：像素取证不可用',
          interpretation: '像素统计检测失败，请结合其他项判断。',
          note: '像素取证不可用。',
        },
        anomaly: {
          status: '有提示·仅参考',
          meaning: '本项：像素统计出现若干「值得人工看一眼」的提示，但不能单独据此下结论。',
          interpretation:
            '下方数值与提示只表示统计形态，手绘、摄影、压缩、截图都可能导致误判。'
            + '必须结合来源凭证、元数据与人工判断，不能单独认定 AI。',
          note:
            '像素统计为最弱信号，跨未知模型与经压缩后极不可靠，假阳性高，易误判。'
            + '此处仅展示测量值与「值得人工复核」的提示；不能单独下结论，需结合其他证据或人工判断。',
        },
        normal: {
          status: '无异常提示',
          meaning: '本项：像素统计未见明显异常提示，但这不等于证明是人作。',
          interpretation:
            '下方原始数值便于了解画面纹理统计。'
            + '没有提示不代表「非 AI」；压缩、未知模型与画风变化都可能掩盖痕迹。',
          note:
            '像素统计为最弱信号，跨未知模型与经压缩后极不可靠，假阳性高，易误判。'
            + '此处仅展示测量值与「值得人工复核」的提示；不能单独下结论，需结合其他证据或人工判断。',
        },
      },
    },
  },
} as const
