# 产品范围：帮助硕博士生读懂论文和项目材料

- 状态：已确认（2026-10-18）；2026-10-22 追加锁定范围。
- 追加锁定（2026-10-22）：Windows-only，不再新增跨平台；阅读语言只保留 English / 简体中文；
  不聚合订阅或 agent，不保留 ChatGPT 本地桥；外部设备/编辑器联动、WebMCP、Markdown 原地
  重折暂不做。
- 本文是取舍与实施顺序，不是逐项需求；每一项实施时仍按
  `/optimize` 的七阶段走（计划、隔离 worktree、独立复核、两份记录、ff-only 合回本地 main）。
- 定位：帮助硕博士生读懂论文和项目材料，围绕一条清楚的使用流程做减法。
- 核心流程：**导入论文或项目材料 → 分层阅读与中英切换、原文对照 → 提问并回查原文 →
  批注与研究阅读卡 → 导出笔记。**
- 术语说明：当前实现是“阅读语言切换 + 原文 PDF 并排”，不是逐句中英双栏；若以后要真正的
  双语对照栏，那是新功能，不在本次范围。
- 本文只确认取舍；删除类改动必须在记录里写清“失去什么”，已有用户数据不删除。

## 1. 确认保留的核心

1. **材料导入**：论文链接/DOI、PDF、DOCX/PPTX/XLSX、CSV/TSV、Markdown/TXT、网页与
   GitHub README、常见图片文字识别；保留 Zotero 导入。论文来源不按学科删除。
2. **分层阅读**：全文、关键句、概括、主题图、单段展开。
3. **阅读语言与原文对照**：简体中文/英文切换、译文、公式、图表、原文 PDF 定位。
4. **有证据的问答**：选段与整篇提问，回答能回到原文。
5. **阅读成果**：高亮、笔记、研究阅读卡、Markdown 导出；整篇 HTML 保存保留为次级入口。
6. **基础文库**：搜索、文件夹、最近打开、安全删除。
7. **支撑能力**：Windows 桌面端、本地服务、数据保存、测试、`tools/zoombench.py`（缩放
   流畅度的唯一测量能力，不能当外围工具清掉）。

## 2. 确认删除（按实施顺序）

### 2.1 API-only 模型接入与可选 Magpie 网关

- 移除所有产品侧命令行 Agent 的发现、模型目录和运行时，包括 Claude Code、Codex 和 Pi。
- 保留 API providers（包括 OpenRouter 等普通 API 服务）；移除 ChatGPT 本地桥。产品不聚合
  订阅，也不驱动 agent。
- 增加可选的外部 Magpie 网关：从 `http://127.0.0.1:3425/v1/models` 动态读取模型，通过 OpenAI 兼容 API 调用；Magpie 可用时优先列出并默认选择其第一个模型。TextFold 不安装、不打包、不管理 Magpie 的账号或订阅。
- 失去：产品内的 ChatGPT 订阅入口和本地桥；用户需要 API key、OpenRouter 或 Magpie。普通 API providers 不受影响。

### 2.2 公开画廊与宣传素材管线，官网压缩

- 删除 `tools/gallery.py`、`tools/gallery.json` 的画廊生成/校对/发布配套，以及
  `tools/readme_assets.py` 的截图、动画素材生产；站点里的 gallery 部分移除。
- 官网压缩成简单的下载、安装、使用说明一页；README 的 demo 链接、已暂停的 `site.yml`
  注释、`docs/DEVELOPMENT.md` 的 gallery 段同步修改。
- 失去：公开演示、跨论文示例、自动制作宣传素材、PyPI 项目页的 Gallery 链接。若以后仍想
  “试一试”，放一个静态样例，不恢复生成管线。

### 2.3 Claude Code / Pi 折叠插件

- 删除 `plugins/textfold/`、`plugins/pi-textfold/` 及安装宣传。
- 同时删除两份 `fold.ts` 必须逐字节相同的不变式与 `tests/test_pi_textfold_same_fold.py`，
  更新 `CLAUDE.md`、`docs/DEVELOPMENT.md`、README 和 `invariants.md`。
- **不删除**摘要、翻译、问答等阅读功能；模型请求通过 API providers 完成，和插件显示功能相互独立。
- 失去：在 Claude Code / Pi 里折叠助手回复；论文阅读器的五级缩放不受影响。

### 2.4 自动段落论证关系（第一步：停止默认生成）

- 从默认生成流程停止 `links` 任务：`pipeline.py` 的调用、`models.TASKS` 与
  thinking 默认值、进度阶段和文案；界面暂时继续显示旧论文已存的 `links`。
- 保留作者写的图表/参考文献跳转，以及问答和阅读卡中的证据链接——它们不是论证关系。
- 失去：新论文不再自动生成“支持/解释/限制”边；少一次模型调用。已有 `links` 数据保留。

### 2.5 第一批格式收窄

- 不再接受新的 RTF、OpenDocument（odt/ods/odp）、旧版 DOC/PPT/XLS 导入；这些格式原本
  只有本地引擎能读，转换成 DOCX/PPTX/XLSX/PDF 很容易。
- 已有文档保留读取与已生成层，不删除用户数据；重新生成时明确提示该格式不再支持。
- **暂缓**：EPUB、MHTML（自研读取器，第二批已复评并
  保留，见第 8 项）。
- 实施时逐项改白名单/界面/文档，不能整块删除 `office.py`。

## 3. 收起或简化（不删底层）

- **模型设置**：主界面只留当前连接、默认模型、连接测试，以及 OpenRouter 一键入口；不再有
  ChatGPT 桥；其他服务商、自定义地址、独立问答模型、推理参数进高级设置。
- **导出**：主入口“导出笔记”（Markdown）和“导出阅读卡”（Markdown）；JSON 作为高级数据
  导出，整篇 HTML 保存和笔记 PDF 放次级菜单。HTML 保存能力保留。
- **命令行 / Agent 接口**：从 README 与首页收起，保留 `python -m textfold get` 和
  `docs/format.md`；桌面启动与测试仍依赖它。
- **段落角色图例**：角色保留，完整图例按需展开。
- **新手教程**：压缩到导入、缩放、回查原文三步，其余就近提示。

## 4. 暂缓或不删除

- **PDF 导入**：2026-10-21 改为只走 MinerU Cloud API。删除本地文字解析、pdf-inspector
  依赖和 MinerU 本地引擎；没有离线回退。PDF 与图片会离开本机。
- **整篇 HTML 保存**：保留，降为次级入口。
- **OFD、TIFF**：本地 MinerU 引擎删除后不再接受新导入；已有文档保留读取，不删除数据。
- **EPUB、MHTML**：2026-10-18 复评后保留；它们是自研读取器代码（26 行和 15 行）、不新增依赖，
  且 EPUB 是 Zotero 的附件路径、MHTML 是浏览器“网页另存为”的格式。没有本地引擎时，删除会
  失去已有文档的重新导入路径。理由与复评条件见
  `docs/changes/2026-10-18-format-reevaluation.md`。
- **Zotero、全部论文来源、文库、问答、阅读卡、高亮笔记、中英切换、原文 PDF 对照**：保留。
- **zoombench、测试、Windows 应用、本地服务、数据目录**：保留。

## 5. 与最初提案不同的三处

1. **OFD 在第二轮随本地引擎一起停止新导入**：它原本只能由本地 MinerU 读取；已有数据保留。
2. **EPUB、MHTML 暂缓**：它们除了引擎，还有 `office.py` 自研读取器；删除要动解析器和
   已有文档兼容，放到第二批。第二批复评（2026-10-18，第 8 项）决定保留，理由见
   `docs/changes/2026-10-18-format-reevaluation.md`。
3. **论证关系分两步**：先停止生成、保留旧数据显示；下个版本再删界面（页边、主题图 chip、
   hover 预览）。已有 `links` 数据留在磁盘，不删。

## 6. 实施顺序与清单

每一项单独 worktree、单独提交、单独记录，完成后 ff-only 合回本地 main；不推送。

- [x] 1. 移除产品侧 Claude Code/Codex/Pi CLI Agent 接入，改为 API-only 并支持可选 Magpie 网关。
- [x] 2. 移除画廊/宣传素材管线，官网压缩为一页（含 README demo 链接与文档同步）。
- [x] 3. 移除 Claude Code / Pi 折叠插件（含 fold-engine 不变式与测试）。
- [x] 4. 停止默认生成段落论证关系（界面暂时保留旧数据）。
- [x] 5. 格式第一批收窄：RTF / OpenDocument / 旧版 DOC/PPT/XLS。
- [x] 6. 设置、导出、命令行入口、图例、教程的收起与简化。
  - [x] 6a. 模型设置：主界面只留当前连接、默认模型、连接测试与 OpenRouter 一键入口，其余进高级。（2026-10-22：ChatGPT 桥改为移除，见第 9 项；OpenRouter 保留。）
  - [x] 6b. 导出：主入口笔记与阅读卡 Markdown，JSON/整篇 HTML/笔记 PDF 进次级菜单。
  - [x] 6c. 从 README 与首页收起命令行/Agent 接口，保留 `textfold get` 与 `docs/format.md`。
  - [x] 6d. 段落角色图例按需展开。
  - [x] 6e. 新手教程压缩为导入、缩放、回查原文三步。
- [x] 7. 移除论证关系的界面（页边、主题图、hover）。
- [x] 8. 再评估 EPUB / MHTML / OFD（只做决定，不默认删除）：EPUB、MHTML 保留；
  OFD 在 2026-10-21 随本地 MinerU 引擎删除而停止新导入。
- [ ] 9. 移除 ChatGPT 本地桥；锁定不再新增语言、跨平台、订阅聚合或 agent 聚合，保留
  OpenRouter 和普通 API providers。执行文档见
  `docs/requirements/2026-10-22-upstream-round.md`。

## 7. 每一项的验收与停止条件

- 验收：`python .claude/hooks/verify.py` 全绿；涉及界面时在浏览器实际检查；涉及删除时
  记录写清失去的能力；有持久化写入的改动带双写者回归测试；中文内容走一遍导入/保存/导出
  不出现编码错误；触及阅读器时写明缩放平滑度未测量（本机没有 playwright 和导出页面）。
- 停止条件：测试无法转绿；复核发现真实的数据丢失或安全问题；某项删除会移除没有替代路径
  的能力（先停下说明）；验证工具缺失导致无法判断（例如平滑度）；用户改变优先级。
- 每一项开始前在回复里说明：模式（optimize/feature）、目标、触及文件、如何验证、失去什么。
