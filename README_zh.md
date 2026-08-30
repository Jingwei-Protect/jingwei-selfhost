# 精卫 Jingwei (Self-host)

**中文说明** | English: [README.md](README.md)

面向画师与数字艺术创作者的**本地化图像归属存证与反 AI 洗图保护工具**。

本仓库为精卫的**独立开源自托管版本**。所有图片计算均在您本地设备上完成，图片不离开本机、不上传任何云端服务器，处理完成后即刻从临时存储中销毁。

*(如需体验创作者社区、在线画廊与云端生态，可访问在线服务 [jwprotect.com](https://jwprotect.com))。*

精卫采用分层防御体系：通过隐形频域与空间域声明（可在验证页完整解析）提供可靠的版权举证链，结合可选的可见扰动图层（如像素位移、微浮雕与动态网格），显著抬高 AI 去水印、局部重绘与随手盗图的成本。

## 功能概览

| 功能模块 | 对应路由 | 详细说明 |
|---|---|---|
| **保护引擎（Protect）** | [`/protect`](http://127.0.0.1:8080/protect) | 上传作品，选择保护模式，自由拖拽水印框或使用橡皮擦/画笔精修主体区域，直接下载保护后的图片（PNG / JPEG）。免注册直接使用。 |
| **全息闪卡（Holo-Card）** | [`/protect`](http://127.0.0.1:8080/protect) | 生成保护图后，支持 3D 炫彩全息倾斜反光交互预览，并支持一键录制导出 `.mp4` 动态全息短视频。 |
| **归属验证（Verify）** | [`/verify`](http://127.0.0.1:8080/verify) | 上传已保护图片，自动检测并分别读出 JW 声明、DWT 频域载荷、LSB 隐写、追踪锚点以及 EXIF/IPTC 元数据。 |
| **实测对比矩阵（Layer Matrix）** | [`/guide/watermark-matrix`](http://127.0.0.1:8080/guide/watermark-matrix) | 内置 9 组常见 AI 洗图与去水印攻击后的前后对比滑杆界面，直观展现防御破坏机理。 |

默认 Docker 镜像**不含** PyTorch 依赖。可选的对抗保护模块（AdvProtect）作为扩展 Profile 独立提供（见文末说明）。

## 安装与快速上手

需要已启动的 [Docker Desktop](https://www.docker.com/products/docker-desktop/)（Windows / macOS）或 Linux 上的 Docker Engine。

```bash
git clone https://github.com/Jingwei-Protect/jingwei-selfhost.git
cd jingwei-selfhost
docker compose up --build
```

首次构建会自动拉取基础镜像并编译前端界面。构建完成后在浏览器中打开 **http://127.0.0.1:8080**。使用期间请保持终端运行；按 `Ctrl+C` 即可停止服务。

> **性能提示：** 图像保护算法包含大量像素级密集计算，笔记本处理超大尺寸图片可能需要数秒。长边超过 2560px 的图片会在上传前自动缩小。若 8080 端口被占用，可在 `compose.yaml` 中修改映射端口。

## 怎么保护一张图

1. 打开 http://127.0.0.1:8080/protect ，上传您的作品（支持 PNG、JPEG 或 WebP 格式）。
2. 输入希望嵌入版权声明的**创作者姓名**（开启 JW 声明时必填）。
3. 选择**基础模式**（见下文详解）。在右侧点击**生成预览**；支持拖拽虚线框，或使用橡皮擦与画笔避开脸部、文字等视觉焦点。
4. 点击**开始保护**，下载保护后的 PNG（无损原图，LSB 验证必备）或 JPEG。
5. *(可选)* 在保护结果下方体验 **3D 全息闪卡交互**，点击**下载闪卡视频 (.mp4)** 导出动态宣传短片。

### 基础模式详解

- **署名·快速（Credit · Quick）** — 针对日常发稿设计。填写作者名后自动写入可验证的隐形 JW 声明。画面印记默认为**自动**（平涂插画 → 浅字符网格；纹理画面 → 位移字），也可手动强制指定**浅字符**或**位移字**。更多图层可在**更多选项**中调节。
- **手动调节（Manual）** — 独立控制每一个隐形层与可见层的开关、不透明度、字号、密度与位移强度。
- **终极·彩色 / 终极·灰阶（Ultimate）** — 针对彩色画作或灰阶线稿预设的多层强化防御配方，可在**终极模式专属设置**中深度调校。

### 署名·快速效果示例

样图仅供说明（[SAMPLES-LICENSE.md](SAMPLES-LICENSE.md)）。

全图视角下整体观感几乎无损。第二行为**同一区域放大**后的效果，红框标注水印的微观结构。

#### 有纹理的作品（毛发、花瓣）→ 自动匹配位移水印

通过算法微移字形路径下宿主像素的坐标，而不是覆盖一层外来色块，最大化保留原作色彩质感。

| 保护前 | 署名·快速之后 |
|:---:|:---:|
| <img src="frontend/public/showcase/credit/credit-dog-before.png" width="400" alt="保护前（小狗）"> | <img src="frontend/public/showcase/credit/credit-dog-after.png" width="400" alt="署名快速后（小狗）"> |

| 同一区域放大（保护前） | 同一区域放大（保护后） |
|:---:|:---:|
| <img src="frontend/public/showcase/credit/credit-dog-face-before-box.png" width="400" alt="小狗脸部放大（保护前），红框为署名位置"> | <img src="frontend/public/showcase/credit/credit-dog-face-after-box.png" width="400" alt="小狗脸部放大（保护后），红框圈出精卫字形"> |

#### 平涂插画 → 自动匹配浅字符网格

采用全图极浅字符点阵结合点状署名印章，在纯色或渐变色块上不易产生违和感。

| 保护前 | 署名·快速之后 |
|:---:|:---:|
| <img src="frontend/public/showcase/credit/credit-cat-before.png" width="400" alt="保护前（猫）"> | <img src="frontend/public/showcase/credit/credit-cat-after.png" width="400" alt="署名快速后（猫）"> |

| 同一区域放大（保护前） | 同一区域放大（保护后） |
|:---:|:---:|
| <img src="frontend/public/showcase/credit/credit-cat-zoom-before-box.png" width="400" alt="猫放大（保护前），红框为点状署名位置"> | <img src="frontend/public/showcase/credit/credit-cat-zoom-after-box.png" width="400" alt="猫放大（保护后），红框圈出点状精卫署名"> |

### 隐形层与追踪层

隐形图层不会在画面留下肉眼可见印记，需在**验证**页面解析。

| 图层名称 | 肉眼外观 | 抗 AI 洗图 / 压缩表现 | 验证提取说明 |
|---|---|---|---|
| **精卫声明（JW）** | 完全不可见 | 抗轻中度 JPEG 压缩与截屏；大面积全图重绘可能受损。 | 解析创作者签名、使用许可限制与时间戳。 |
| **DWT 频域载荷** | 完全不可见 | 频域写入（支持字母/数字/符号，最长 24 字）。抗压缩性能显著优于 LSB。 | 完整读出嵌入的载荷字符串。 |
| **LSB 空间域隐写** | 完全不可见 | 无损位平面嵌入。**仅对 PNG 原图有效**（转换为 JPEG 或截图后失效）。 | 提取空间位流。 |
| **追踪锚点** | 四角极浅锚点 | 截图或裁切后，若在验证页输入**保护时使用的完全一致的署名**，仍可提取作者识别码与保护年月。（要求短边 ≥ 512px）。 | 识别作者码与保护时间。 |
| **EXIF / IPTC 元数据** | 标准元数据 | 原图直传可保留；多数社交平台转发时会自动剥离。 | 标准元数据读取。 |

### 可见图层实测矩阵

可见层旨在增加 AI 局部修补与去水印算法的处理难度，迫使抹除过程产生结构性破坏与明显杂色。

*左列：精卫加水印后。右列：AI 去水印/局部重绘抹除后。右侧红框标出涂抹、色块、残余痕迹或结构错位。*

在线交互滑杆对比：http://127.0.0.1:8080/guide/watermark-matrix

#### 位移水印 · 铺满重复

在全图阵列上推移像素结构并保留原始色彩。AI 尝试抹除文字时，受损的纹理连续性难以无痕重建。

| 精卫加水印效果 | AI 试图修复后 |
|:---:|:---:|
| <img src="frontend/public/showcase/guide/disp-repeat-protected.png" width="400" alt="位移铺满 — 保护后"> | <img src="frontend/public/showcase/guide/disp-repeat-ai-restored.png" width="400" alt="位移铺满 — AI 修复后"> |

#### 位移水印 · 随机分散

将字符分散嵌入高方差区域，破坏局部边缘引导，增加大模型重绘对齐的难度。

| 精卫加水印效果 | AI 试图修复后 |
|:---:|:---:|
| <img src="frontend/public/showcase/guide/disp-scatter-protected.png" width="400" alt="位移分散 — 保护后"> | <img src="frontend/public/showcase/guide/disp-scatter-ai-restored.png" width="400" alt="位移分散 — AI 修复后"> |

#### 位移水印 · 集中整词

在主体或重点位置布置整词形变，支持在保护页画布上自由拖拽虚线框定制位置。

| 精卫加水印效果 | AI 试图修复后 |
|:---:|:---:|
| <img src="frontend/public/showcase/guide/disp-tile-protected.png" width="400" alt="位移整词 — 保护后"> | <img src="frontend/public/showcase/guide/disp-tile-ai-restored.png" width="400" alt="位移整词 — AI 修复后"> |

#### 平铺文字

半透明阵列文字，提供鲜明的视觉威慑与版权直观宣告。

| 精卫加水印效果 | AI 试图修复后 |
|:---:|:---:|
| <img src="frontend/public/showcase/guide/text-tile-protected.png" width="400" alt="平铺文字 — 保护后"> | <img src="frontend/public/showcase/guide/text-tile-ai-restored.png" width="400" alt="平铺文字 — AI 修复后"> |

#### 浮雕纹理

全图微立体斜向浮雕划线，可使 AI 局部重绘算法产生大面积不自然的过渡断层。

| 精卫加水印效果 | AI 试图修复后 |
|:---:|:---:|
| <img src="frontend/public/showcase/guide/emboss-protected.png" width="400" alt="浮雕 — 保护后"> | <img src="frontend/public/showcase/guide/emboss-ai-restored.png" width="400" alt="浮雕 — AI 修复后"> |

#### 模糊条

横向半透明保护带。常用于人像面部、商稿交付预览或遮蔽敏感结构。

| 精卫加水印效果 | AI 试图修复后 |
|:---:|:---:|
| <img src="frontend/public/showcase/guide/ascii-protected.png" width="400" alt="模糊条 — 保护后"> | <img src="frontend/public/showcase/guide/ascii-ai-restored.png" width="400" alt="模糊条 — AI 修复后"> |

#### 模糊块

自由画笔涂抹色块模糊。可在画布上自定义涂刷遮蔽区域。

| 精卫加水印效果 | AI 试图修复后 |
|:---:|:---:|
| <img src="frontend/public/showcase/guide/dots-protected.png" width="400" alt="模糊块 — 保护后"> | <img src="frontend/public/showcase/guide/dots-ai-restored.png" width="400" alt="模糊块 — AI 修复后"> |

#### ASCII 水印

满屏极浅字符网格与微型签名，通过密集的高频纹理干扰边缘检测算法。

| 精卫加水印效果 | AI 试图修复后 |
|:---:|:---:|
| <img src="frontend/public/showcase/guide/moire-protected.png" width="400" alt="ASCII — 保护后"> | <img src="frontend/public/showcase/guide/moire-ai-restored.png" width="400" alt="ASCII — AI 修复后"> |

#### 半调网点

在背景中嵌入高频微点阵，AI 平滑去噪后极易留下不自然的灰度块面。

| 精卫加水印效果 | AI 试图修复后 |
|:---:|:---:|
| <img src="frontend/public/showcase/guide/halftone-protected.png" width="400" alt="半调 — 保护后"> | <img src="frontend/public/showcase/guide/halftone-ai-restored.png" width="400" alt="半调 — AI 修复后"> |

*(保护页还支持：人像脸部浮雕锁、跳跃摩尔纹、位移 Logo 轮廓形变等丰富图层)*

## 怎么验证

1. 打开 http://127.0.0.1:8080/verify ，上传您下载的保护文件（验证 LSB 时请使用原始 PNG）。
2. 上传后系统自动进行多层解码，展示 C2PA 声明（若包含）、JW 声明、追踪锚点、DWT 频域、LSB 隐写和 EXIF/IPTC 元数据。
3. 针对二次截屏或裁切后的图片，在追踪锚点处输入**保护时填写的同一段创作者署名**即可发起签名比对。

## 许可证

- **程序代码：** [MIT](LICENSE) © 精卫 Jingwei
- **展示样图**（署名示例与矩阵对比图）：**非 MIT。** 遵循 [SAMPLES-LICENSE.md](SAMPLES-LICENSE.md) 保留所有权利，仅供功能文档展示，禁止用于商业素材、作品集或 AI 模型训练。

---

## 可选对抗保护（AdvProtect）

默认 Docker 镜像保持轻量，**不包含** PyTorch 及大型深度学习框架。

针对学术与深度防御测试，项目提供了基于潜在特征/扩散扰动的对抗保护 Profile（AdvProtect）。请注意：由于云端商业改图工具（如豆包、即梦等）包含复杂的服务端预处理与二次重重编码，对抗样本**无法承诺在所有商业模型上完全生效**。

如需启用对抗保护 Profile：

```bash
docker compose down
docker compose -f compose.yaml -f compose.adv.yaml up --build
```

详细技术说明与使用文档参见 [docs/adv-protect-local.md](docs/adv-protect-local.md)。
