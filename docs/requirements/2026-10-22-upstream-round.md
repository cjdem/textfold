# 上游移植轮次：2026-10-22

- 状态：待执行（最终审核后启动）
- 审阅记录：`docs/upstream/2026-10-22.md`
- 范围：该记录中“最终实现顺序（待审核）”的 23 项，加上 fork-specific 的 R0（移除 ChatGPT 本地桥）。
- 执行方式：在新窗口用 `/loop`，每轮只做一个任务；完成本地合并后勾选并记录；不 push。
- 上游：`chenxiachan/textfold`，HEAD `7e40a94`（v0.10.22）；2026-10-22 复查没有更新提交。

## 锁定范围（不可越过）

- Windows-only；不再新增跨平台。
- 阅读语言只保留 English / 简体中文；不新增阅读语言。
- 不聚合订阅或 agent；不保留 ChatGPT 本地桥；不新增 agent runtime。
- 普通 API providers（Anthropic、OpenAI-compatible、OpenRouter、Ollama 等）保留；
  Magpie 只作为外部 OpenAI-compatible provider 调用，产品不管理它的账号或订阅。
- 外部设备/编辑器联动（`textfold://`、Obsidian、`server.json`、`/api/doc`、拖出链接、
  citekey 暴露）、WebMCP、Markdown 原地重折暂不做。
- 每项独立 worktree、独立测试、独立记录、独立本地合并；不 push。
- 删除类改动必须在记录里写清“失去什么”；已有用户数据不删除。
- 触及阅读器时，zoom 平滑度按 CLAUDE.md 标“未测”，不能声称不受影响。

## Loop 启动

在新窗口运行（间隔按任务时长调整，建议 20–30 分钟）：

    /loop 25m 读取 docs/requirements/2026-10-22-upstream-round.md，按其中的循环规则执行下一个“待做”任务；一次只做一个，完成本地合并后勾选并记录；全部完成或阻塞时停止 loop。

把下面这段作为该窗口的固定执行提示词：

    你是本轮上游移植的执行代理。先读 CLAUDE.md、docs/WORKFLOW.md、
    .claude/skills/optimize/SKILL.md、docs/requirements/product-scope.md 和本文件。

    1. 先看 git status 和 worktree。如果只有本轮这几份 docs 的未提交改动（本文件、
       docs/upstream/2026-10-22.md、docs/upstream/README.md、docs/requirements/product-scope.md、
       docs/requirements/provider-only-magpie.md），先把它们作为本轮计划提交（不 push），再开始
       R0；其他未提交改动或未合并 worktree 则停止并报告，不要开始新任务。
    2. 在“任务总表”里找第一个状态为“待做”的任务；没有则停止 loop 并报告全部完成。
    3. 把该任务状态改为“进行中”，按任务指定的 /optimize 或 /feature 完整流程执行：
       计划确认、隔离 worktree、实现、测试、文档、textfold-verifier、记录、本地合并。
       计划阶段按工作流等我确认；确认后自动做到本地合并。不要 push。
    4. 合并后运行 `python .claude/hooks/verify.py`，记录测试数、commit、verifier 结果；
       把任务状态改为“完成”，填写执行记录，并提交这次文档更新。
    5. 本轮只做这一个任务，结束后停止；不要在同一轮开始下一个任务。
       遇到测试失败、数据丢失风险、安全问题或需要我决定的事，把状态改为“阻塞”并停止。

默认保留计划确认点。如果想无人值守，把第 3 步的“计划阶段等我确认”改成“计划写入任务记录后继续”；删除能力、数据丢失和安全问题仍必须停下来。

## 任务总表

状态只用：`待做` / `进行中` / `完成` / `阻塞`。执行时只改本表和执行记录。

| ID | 状态 | 模式 | 任务 | 上游 / 来源 | 依赖 | 规模 |
|---|---|---|---|---|---|---|
| R0 | 完成 | optimize | 移除 ChatGPT 本地桥；保留 OpenRouter 和普通 API providers | fork-specific | 无 | 中 |
| R1 | 完成 | optimize | 本地服务器 Host 校验（DNS rebinding） | `4fee928` | 无 | 小 |
| R2 | 完成 | optimize | 所有文本读写显式 UTF-8 | `c1b3fd3` | 无 | 中 |
| R3 | 完成 | optimize | 旧 TextFold 的 GBK 库按代码页读入，下一次保存写 UTF-8 | `4f15560` | R2 | 中 |
| R4 | 完成 | optimize | 只支持流式的 API 服务 | `8e7569b` | 无 | 中 |
| R5 | 完成 | optimize | 模型回复的多种 JSON 形状 | `09e9d37` | 无 | 中 |
| R6 | 完成 | optimize | `TEXTFOLD_NO_MODELS` 下不调用模型 | `1761a95` | 无 | 小 |
| R7 | 完成 | optimize | EPUB 章节先解码再解析 | `13d7794` | 无 | 小 |
| R8 | 完成 | optimize | 翻译漏段重试（只取 `d457cfa` 的翻译部分） | `d457cfa` | 无 | 中 |
| R9 | 完成 | optimize | 应用 payload 带 Anthropic SDK | `f260244` | 无 | 小 |
| R10 | 完成 | feature | 多文件导入：逐文件队列，不用 MinerU batch | `f0c731d` | R1–R9 | 中 |
| R11 | 完成 | feature | 可配置 MinerU v4 base URL，默认官方 | `77a2344` | R10 后或并行 | 小 |
| R12 | 完成 | feature | self-hosted V1 adapter（条件项） | fork-specific（不做） | R11；仅确有自部署时 | 大 |
| R13 | 完成 | feature | 中文 Brief 句子切分 | `770fb08` | R4/R5 之后 | 中 |
| R14 | 完成 | feature | 中文五级折叠 | `4897e24` | R13 | 大 |
| R15 | 完成 | optimize | CJK 规则只作用于中日文 | `6e2cada` | R14 | 中 |
| R16 | 完成 | feature | Aa 菜单 + 缩放沙箱 font/width | `f76eb4d` + `c38804e` | R14/R15 之后 | 中 |
| R17 | 完成 | feature | 主题、行距、阅读位置、专注模式 | `e5bd668` + `a670e57` + `920a270` | R16 | 中 |
| R18a | 完成 | feature | 标题层级 | `fb9f95c`（标题部分） | R16/R17 | 小 |
| R18b | 完成 | feature | Topic 分组 / 思维导图 | `fb9f95c`（地图部分） | R18a | 大 |
| R18c | 完成 | feature | margins 开关（问答 / 笔记；链接本 fork 已移除） | `fb9f95c`（margins 部分） | R16 | 小 |
| R19 | 待做 | feature | 侧栏固定 | `b977bba` | R16/R18c | 中 |
| R20 | 待做 | feature | 整篇文本按当前层级/语言存 Markdown | `7d94f25` | R16 后 | 中 |
| R21 | 待做 | feature | 批量删除/恢复 + 侧栏多选 | `15d7b8a` + `d80e779` | 无 | 中 |
| R22 | 待做 | feature | 文档命名 + 整篇笔记（可选） | `d457cfa` | 低优先 | 中 |
| R23 | 待做 | feature | 嵌套文件夹（可选） | `d457cfa` | 低优先；当前一层已可用 | 中 |

## 任务详情

### R0 · 移除 ChatGPT 本地桥

- 目标：产品不再聚合订阅或 agent；移除 ChatGPT 本地桥，保留 OpenRouter 一键授权和普通 API providers。
- 清理：
  - `textfold/bridges.py` 的 ChatGPT bridge 部分（`BRIDGE`、`BRIDGE_PACKAGE`、`bridge_status`、
    `bridge_provider`、`bridge_start`、相关 probe）；OpenRouter OAuth 保留，可留在原文件或移到
    `textfold/openrouter.py`，更新 import。
  - `textfold/procenv.py` 若只服务 bridge，删除；若仍被其他代码使用，保留并改注释。
  - `textfold/providers.py` 的 `chatgpt-bridge` preset；`textfold/models.py` 的 bridge provider、
    `bridges.bridge_status`、默认模型注释里的 ChatGPT plan 偏好（若是 OpenAI API 模型则保留）。
  - `textfold/server.py` 的 `/api/bridge`、`/api/bridge/start`、`bridge` 状态字段；保留
    `/api/openrouter/*`。
  - `textfold/web/app.js`、`textfold/web/i18n.js` 的 bridge 卡片、设置行、启动轮询、`cn_gpt`、
    `bridge_*` 文案；保留 OpenRouter。
  - `README.md`、`README.zh-CN.md`、`docs/DEVELOPMENT.md`、`site/build.py` 及生成物里的
    ChatGPT bridge / ChatGPT plan 文案；重建站点，不部署。
  - 测试：`test_landing_page.py`、`test_magpie.py`、`test_agents_scope.py`、
    `test_agents_windows.py` 里的 bridge 专用部分；保留 OpenRouter 和其他 provider 测试。
- 验收：产品代码/文档不再出现 `openai-oauth`、`127.0.0.1:10531`、`chatgpt-bridge`、
  `ChatGPT bridge`；OpenRouter 一键授权、Magpie、其他 API providers 和 PDF 转换仍可用；
  `python .claude/hooks/verify.py` 全绿。
- 记录必须写清失去：**ChatGPT 订阅入口**；用户需要 API key、OpenRouter 或 Magpie。

### R1–R9 · 基础正确性

按 `docs/upstream/2026-10-22.md` 的 A 表执行；每项独立提交、独立记录。重点：

- R1：Host 校验和 `tests/test_server_host.py`。
- R2/R3：先显式 UTF-8，再迁移旧 GBK 文件；中间不要发版。
- R4/R5/R6：流式、回复形状、`TEXTFOLD_NO_MODELS`；都带对应测试。
- R7：EPUB 先 `_decode` 再 `_fragment`。
- R8：只取 `d457cfa` 的翻译漏段重试；文档命名/整篇笔记/嵌套文件夹另做。
- R9：MyGo payload 的 `requirements.txt`/安装步骤带上 `anthropic`，不要照搬 Electron 文件。

### R10 · 多文件导入

- 用现有逐文件 `/api/files` + `Jobs.convert` 队列；每个文件一个 job，转换队列一次一个；每文件保留进度、停止、重试。
- 不用 MinerU 的 200 文件 batch；不为多文件改协议。
- 浏览器一次拿到多个 `File`，逐个上传；侧栏逐个显示；toast 汇总成功/失败/等待。
- 每次最多 50 个；重复 pid 跳过；当前 100 MiB 上限保留；600 页和每天 2,000 页优先额度在提示里说明。
- 验收：多文件拖入、队列顺序、单文件停止/重试、失败提示、侧栏状态、无并发写冲突。

### R11 · MinerU v4 base URL

- `models.py` 增加 `mineru_api_url`，默认 `https://mineru.net/api/v4`。
- `engine.py` 不再硬编码 `API`；从设置读 base，校验 `http(s)://`、去掉末尾 `/`；`engine.status()` 报告 base。
- 设置页 MinerU 区域增加 URL 输入和“恢复官方地址”；保存走 `/api/settings`。
- 只支持 v4 兼容端点；自部署 `mineru-kit` 是 V1，不在这一步假装支持。
- 验收：默认官方、自定义 v4、非法 URL 拒绝、生成/转换走新 base、测试覆盖。

### R12 · self-hosted V1 adapter（条件项）

- 只有确实要接 `mineru-kit api-server` 时做；不做则保持 R11 的 v4-only。
- 接口：`/v1/file_parse`（同步，`wait_timeout` 1–3600，默认 300）或 `/v1/tasks`（异步）；不是 `/api/v4/file-urls/batch`。
- 限制：200 MiB/文件、100 文件/任务；ZIP 输出需要 `response_format=zip` / `output_formats=zip`；本地可无 key。
- 增加 `mineru_api_mode`（`cloud` / `self-hosted`，默认 cloud），或等价机制；处理 `http://` 本地地址、multipart 上传、任务轮询和输出映射到现有 `structured_content.json`。
- 验收：本机 `mineru-kit` 起服务后能转换一份 PDF；输出与云端路径一样进入 `pdfdoc.store_pdf`；测试不依赖真实服务。

### R13–R23 · 中文/阅读/生产力

按 `docs/upstream/2026-10-22.md` 的最终顺序表执行；每组都带对应测试和手测。特别是：

- R13→R14→R15 顺序不能反；R16 在它们之后动 `reader.js`。
- R16→R17→R18a→R18b→R18c→R19 是阅读器依赖链；R18 按审阅建议拆成标题层级、Topic 分组/思维导图、margins 三次。
- R20/R21 独立；R22/R23 是可选，审核时可删。
- 触及阅读器的任务在记录里写“zoom 平滑度未测”。

## 执行记录

| 日期 | 任务 | 模式 | 本地 commit | 测试 | verifier | 备注 |
|---|---|---|---|---|---|---|
| 2026-10-22 | R0 | optimize | `b4140d8` | 206，OK | 无阻断发现；1 处 UI 缺陷、3 处测试缺口已修 | 移除 ChatGPT 本地桥，OpenRouter 移到 `textfold/openrouter.py`；失去产品内订阅入口；zoom 平滑度未测 |
| 2026-10-22 | R1 | optimize | `0507bda` | 211，OK | 无阻断发现；测试观察面、死代码与 docstring 已补 | Host 校验在 `do_GET`/`do_POST` 路由前，其他名字 421；`localhost.`、`127.0.0.2` 等按设计拒绝；不涉及阅读器 |
| 2026-10-22 | R2 | optimize | `4f8eff6` | 214，OK | 无阻断发现；1 个数据安全问题、1 个钩子编码问题、若干措辞/测试已修 | 所有文本 I/O 显式 UTF-8；命令行导入支持 GBK/BOM/CRLF；GBK 的 library/zotero 不再被静默清空；旧文件迁移留给 R3 |
| 2026-10-22 | R3 | optimize | `02bc0e2` | 222，OK | 两轮：第一轮推翻“读时写回”（比较与替换非原子，会丢并发保存），第二轮修完记录/测试/文档的 7 处问题；无阻断发现 | 与计划不同：读只解码不写（GBK 文件保持原样，下一次保存写 UTF-8），两边都无法解码的文件报错而非用替换字符后保存；`store.codepage()` 在 3.9/3.10 用 GetACP，不再受 UTF-8 模式影响；`zotero.apply` 改临时文件+替换；未触及阅读器，zoom 平滑度未测 |
| 2026-10-22 | R4 | optimize | `0aacd72` | 239，OK | 三轮：第一轮发现重试路径读截断错误体、200 错误体让“流式+无 JSON 模式”形状不可达（都已修）；第二、三轮修记录措辞与测试强度；无阻断发现 | SSE 回复合并成一个 completion；只有被拒后才加 `stream`，所有旧形状的首请求逐字节不变；`_content` 留给 R5，仅内联“200 不是 completion 就前进”；流式请求通常没有 usage，成本记不到；未触及阅读器，zoom 平滑度未测 |
| 2026-10-22 | R5 | optimize | `d46d2cb` | 257，OK | 三轮：第一轮发现非对象翻译回复会静默保存不完整层、单 chunk 文档不回退；第二轮发现 pipeline 对请求语言忽略 `failed`、守卫测试空转；第三轮修测试强度；无阻断发现 | 回复按 list / JSON 字符串 / id-keyed / 字符串 section / parts 读；读不出的 chunk 本地回退并丢弃缓存；请求语言的失败部分不保存为当前；失败任务最后 12 行日志 print 到 stdout（MyGo 的 server.log）；未触及阅读器，zoom 平滑度未测 |
| 2026-10-22 | R6 | optimize | `81d9661` | 259，OK | 无功能发现；记录里从上游继承的例子（命令行旧默认、agent runtime）在本 fork 不存在，已改成实际可达的“直接持有 spec”；“保留的回复仍会读”限定到 spec 形式；无阻断发现 | `llm.call` 在缓存读取之后、调用模型之前检查 `TEXTFOLD_NO_MODELS`，任何 spec 都不再发请求；`force` 拒绝；测试里两个 mock 模型的用例临时清掉该变量；未触及阅读器，zoom 平滑度未测 |
| 2026-10-22 | R7 | optimize | `6606177` | 269，OK | 三轮：第一轮否决一行移植（head title 进正文、声明编码/UTF-16 读错）；第二轮发现标准 `encoding=` 声明让 lxml 拒绝整章、长注释绕过文档判断；第三轮只余措辞；无阻断发现 | 章节按 BOM、XML 声明或 meta charset 解码再解析；`_fragment` 先剥声明/注释/处理指令再判断整篇文档，head title 不进正文；SVG 章节保留文字；空章节跳过（以前整本 bad-file）；已转换的旧 EPUB 重新转换会丢层；未触及阅读器，zoom 平滑度未测 |
| 2026-10-22 | R8 | optimize | `c6e6b4b` | 282，OK | 一轮长审查 + 一次窄复查：阻断项是单节文档“所有首轮调用失败”时在重试前就抛出（已改为先重试、两轮都失败才抛，并加测试）；高优先项是重试可能读回同一提示下缓存的漏段回复（已改为重试 `force=True` 真问模型）；其余（force 会用带缺口的层覆盖完整层、fill 全失败会让 job 失败而 also_zh 只记日志、`Jobs._same` 不看 force、单字母段落不算缺口）记入记录；窄复查确认修复正确、无新阻断 | 只取 `d457cfa` 的翻译部分：构建时漏段/失败调用立刻补问，存储层记录 `meta.gaps` 并在下次生成或打开该语言时只补缺口；阅读器显示“N 段未译”，应用打开时自动补译（每标签页每计数一次）；R5 的“失败 part 不保存”改为“带缺口保存后补齐”；`assemble` 的 takeaway 回退；未测 zoom 平滑度；记录见 `docs/changes/2026-10-22-translation-gaps.md` |
| 2026-10-22 | R9 | optimize | `adac02e` | 282，OK；`go test ./...` 4 包 OK | 无阻断：verifier 在现有 payload 的 CPython 3.12 副本上跑了真实安装和最终 import 检查（`payload ok 1.17.0`）；指出 Go 测试过脆（已改成正则并钉住 `-s`/`app/`）、“应用没有 pip”说法不实（payload 带 pip 26.2.2，只是应用没有运行它的途径；已改文案）、包数与体积（+42 MB，已记）；`pyproject.toml` 的 `anthropic` extra 未钉版本属既有漂移，记入 Pitfalls | 只改 MyGo payload：`prepare-payload.mjs` 安装 `anthropic>=1.15,<2` 并在构建时 import 检查；`app/requirements.txt`、README、DEVELOPMENT 更新；新增 Go 测试钉住安装/检查契约；未照搬 Electron 文件；未重建完整 payload/安装包，未调用真实 Anthropic API；记录见 `docs/changes/2026-10-22-anthropic-sdk-payload.md` |
| 2026-10-22 | R10 | feature | `f0c731d` | 284，OK | 两轮 + 一次窄复查：第一轮阻断（阅读页批量重画生成 toast，生成 watcher 在下次轮询抛错、watcher 不删除、侧栏不再更新）已改为独立 `fileToast`，并让生成 watcher 在 toast 被重画时重建自己的阶段/进度并把 toast 显示出来；第二轮发现单文件重试走了单文件路径（已改 `beginBatch`）、文本导入成功但生成调用失败后重试被当成“已添加”（重试时重新提交）、watcher 守卫未覆盖 `closable` 重画后缺进度条、批量文本超 JSON 上限报成 PDF 超 100 MB、重复兜底停止可能停掉别的标签页的 job（只停本页上传前不知道的 job）、`doc-` 前缀未钉（新增契约测试）、排队批次显示上一批进度（等待行）；窄复查确认无阻断，余下两项（上传期间别的页面新建的 job 不在快照里、重试文本可能多排一个 job）记入 Pitfalls | 浏览器逐文件上传到现有 `/api/files` 与 `/api/import`，每个文件一个 job，转换/生成队列各一次一个；最多 50 个；按内容 pid（SHA-256 前 16 位）在浏览器提前跳过重复，文本按导入 id 在导入后跳过；失败的上传/转换可从汇总重试；阅读页批量用独立 toast；侧栏逐文件进度/停止；MinerU 600 页/每天 2,000 页提示；未测 zoom 平滑度；记录见 `docs/changes/2026-10-22-multi-file-import.md` |
| 2026-10-22 | R11 | feature | `77a2344` | 299，OK | 一轮 + 窄复查：无阻断。首轮发现手改孤立代理项让 `/api/models` 的 JSON 编码失败（已修：`status()` 替换不可编码字符）、非文本值被当成空/重置（已修：读拒绝、保存 400；文件里 null 仍视为没值）、记录里设置页圆点描述过时、旧需求文档仍像当前规则、测试数写错、poll 未覆盖、`https://@host` 被接受；窄复查确认七项已修，另修 null 文案与“代理项在路径末尾可被存成截断地址”（`base_ok` 连空的 `?`/`#` 也不收） | `mineru_api_url` 设置，默认 `https://mineru.net/api/v4`；`engine.base_ok` 校验/规范化（http(s)、host、无 query/fragment/登录信息/空白、去尾部 `/`）；非空不可用值在转换前以 `bad-mineru-url` 失败、不回退官方；`status()` 报 `base`/`official`/`baseOk` 且不抛；一次转换固定一个 base；`_put` 按签名 URL 的 scheme/port；设置页地址输入/保存/恢复官方；CLI 打印地址；只支持 v4，V1 留给 R12；未测真实自定义网关和 zoom 平滑度；记录见 `docs/changes/2026-10-22-mineru-base-url.md` |
| 2026-10-22 | R12 | feature | —（不做） | — | — | 条件项评估后不做：本机没有 `mineru-kit`，也没有自部署 MinerU 的需求；R11 的 `mineru_api_url` 已覆盖 v4 兼容网关。按任务写明的“不做则保持 R11 的 v4-only”，未实现 `/v1/file_parse`、`/v1/tasks`、multipart、200 MiB/100 文件或 ZIP 输出映射。 | 无代码改动；`mineru-kit` 自部署仍不支持；确有需要时另开任务；R11 的地址设置保持。 |
| 2026-10-22 | R13 | feature | `979c7ab` | 318，OK | 一轮 + 窄复查：首轮发现纯英文边界会因 ASCII `'` 与连续收尾符而改变（超过 12 句的英文段可能被切、后续 unit id 移动），以及 `cjk_heavy` 的“id 不移动”对混合段不成立——两条阻断；已改为按单元分派（无 CJK/。！？ 的单元走旧切分器），并修正文档、明确混合段“知情保留”；另修 guard 只数汉字（现随切分器含假名）、空 ladder 回退本地层、长段测试未钉 id；窄复查确认两条阻断已解，30k 纯 ASCII fuzz 与 main 0 差异，无新问题 | 含 CJK 或 。！？ 的单元按 。！？ 切句；纯英文单元仍走旧切分器（句号、编号、分段不变）；长 CJK 段不切块（提前取 `4897e24` 的 `cjk_heavy`，R14 不再取该 hunk）；`full` 改为单元原文，中文 Full 不再插入空格；`apply_en` 丢弃越界 evidence 并以首句回退；混合中英文段落仍可能改变分段（知情保留，重新生成）；未测 zoom 平滑度；记录见 `docs/changes/2026-10-22-chinese-brief.md` |
| 2026-10-22 | R14 | feature | `e88c516` | 354，OK | 一轮 + 窄复查：首轮确认英文逐字节不变（本机英文论文 92 unit/16 chunk 的 prompt、local、assemble、section_ladder 与整次 build 全同），发现两条阻断——目录行成为下一段 Brief 的 glue、以 `……` 结尾的段落被当作断句；已修（`dress` 回溯时跳过 apparatus；`…` 计入 WHOLE）。另修目录点线把含 `…………` 的论点误判为 apparatus（现要求行末页码）、翻译的 section topic 预算被源文档覆盖（`section_ladder` 保留调用方预算，build 传文档预算）、主题丢掉 `P2P`/`3.5`/`第一章`、atom 变 `[object Object]` 并丢 glue、隐藏 unit 的笔记跳转零矩形、被抑制单元仍被补译、`tn=0` 仍在 Topic 显示、过时注释与 DEVELOPMENT 描述；窄复查确认两条阻断已解、无新问题，354 OK | 按单元/小节分派：中文（含日文假名）单元用字符预算（40/60/8/40）、claim 句、apparatus 抑制、背景降级、跨页 glue 和中文提示；英文文档的提示、层级与页面不变（逐字节比较）。未取 R15 的 `cjk_doc`/`meta.cjk`、reader 的 stake/ref/Topic 滚动、`l3` 移除和 `1.研究背景` 守卫；中文经 `tr-zh` 阅读时仍无 glue/l3。未测 zoom 平滑度；记录见 `docs/changes/2026-10-22-chinese-five-levels.md` |
| 2026-10-23 | R15 | optimize | `7fcadc6` | 362，OK | 一轮，无阻断发现；英文逐字节不变（本机英文论文 92 unit/16 chunk 与 5 个英文/混合 fixture 的 mocked build 全同，层内无 `tn:0`/`l3`）。非阻断：中文论文里的英文段被 glue 拼成 `conditionThe`（已修——`dress` 只在两半都是 CJK 时拼接，加测试）、前 4000 字符采样会把英文摘要后的中文正文读成英文（上游继承，测试钉住并记入 Pitfalls）、`1.研究背景` 守卫只在句首生效（注释与文档如实描述）、gate 边界与 store 的 `cjk` 参数缺测试（后者经 `store.assemble` 已补）、记录高估了 `pieces` 只算一次（已改正）、旧层句子重编号（DEVELOPMENT 已警告） | 文档级 `cjk_doc`/`meta.cjk`；`l3`/`LISTY`/`_listy` 移除，降级单元在 Brief 与 Key 可读、Takeaway/Topic 隐藏；reader 的 CJK 规则全部按 `CJK_DOC` 生效（标记剥离、apparatus 隐藏、ref 小节、Brief 的 stake、Topic 滚动、空 stake）；`1.研究背景` 不再断句；浏览器核对中文页 Brief/Topic 与英文页 Brief 均符合预期；未测 zoom 平滑度；记录见 `docs/changes/2026-10-22-cjk-document-gate.md` |

| 2026-10-23 | R16 | feature | `534d1a7` | 366，OK | 一轮：1 条阻断——`mirrorType` 只镜像了 font/width，而字号是 `<html>` 上的内联 `--fs`，沙箱样式表里的 `:host { --fs: 1 }` 会盖过继承值，非默认字号下相邻关键帧按 100% 布局、缩放末尾错位（verifier 在 headless Chrome 复现：108% 时页面 740px/19.98px、沙箱 700px/18.5px）；已修——把 `--fs` 内联到沙箱宿主并加测试。另修：沙箱缺 `app` 类使 MyGo 应用里 `--colmax` 与页面不同（现镜像 `app`/`compare`）、点击笔记/导出/图例时 Aa 菜单不关（改为捕获阶段监听）、保留高亮/段落预览/引用/笔记列表高亮仍用衬线（改用 `--text`）、记录声称 DEVELOPMENT 写了打印重置而实际没写、`invariants.md` 仍把“衬线=作者”写成单一规则（均已补） | 阅读器 Aa 菜单：字号 86%–135%（整栏随之缩放）、栏宽窄/标准/宽（`--colmax` 给边注留位）、作者文字衬线/无衬线；存于 `localStorage`（每浏览器、每篇通用）；缩放沙箱 `mirrorType` 同步 font/width/`--fs` 与 `app`/`compare`；打印恢复默认字号。浏览器核对中文界面、108%→740px、窄栏 648px、无衬线生效、重置与持久化、关闭方式；预览面板不跑 rAF，缩放动画与末尾对齐按机制核对、未目视；未测 zoom 平滑度；记录见 `docs/changes/2026-10-22-reader-type-menu.md` |

| 2026-10-23 | R17 | feature | `d86253d` | 370，OK | 一轮：1 条阻断——`card.css`（本 fork 专属的阅读卡抽屉）的深色规则只跟系统，浅色主题下深色系统会出现浅底浅字（对比度约 1.6–1.8:1）；已修（每条规则同时按 `html[data-theme="dark"]` 生效并加契约测试）。非阻断：两个标签页写位置映射可能互相覆盖（localStorage 无 CAS，记入 Pitfalls）、新 CSS 测试原先无法失败（已改为断言 `var(--lh, 1)`、不再有 `:not([data-theme="light"])`、paper 的系统深色规则、卡片规则）、字体就绪后的第二次回位会打断已滚动的读者（现在位置移动后不再回位）、`color-scheme` 只跟显式选择（已补系统深色）、落地页忽略旧 `theme` 键（app.js 已同步映射）、Aa 对话框无障碍名仍是“字号、栏宽和字体”（已改“阅读外观”）、DEVELOPMENT 对 `--lh` 覆盖范围说过头且守卫里的 `#s=` 无页面使用（已改） | 明暗（跟随系统/浅/深）+ 风格（默认/纸张）可组合、行距紧凑/标准/宽松（`--lh`）、阅读位置（`localStorage` `textfold.pos`，回位提示与进度线）、专注模式（F/Esc，边缘唤回）；app 落地页同步主题；未目视回位/进度线/触摸唤回（预览面板无 rAF），未测 zoom 平滑度；记录见 `docs/changes/2026-10-22-reader-theme-focus.md` |

| 2026-10-23 | R18a | feature | `441883c` | 373，OK | 一轮，无阻断；测试强度三项已修（断言 `calc(… * var(--fs))`、边距与内边距、`looks()` 复制阴影、Topic 卡片所有带阴影的标题规则都取消），DEVELOPMENT 措辞过头已改；另指出 640px 以下论文标题上限 26px 低于节标题 27px（上游原样，记入 Pitfalls）；一次全量测试出现本地 socket 的 `ConnectionAbortedError`，连续两次重跑 373 OK，与本改动无关 | R18 按审阅建议拆成三次（R18a 标题层级、R18b Topic 分组/思维导图、R18c margins）；本次只取 `fb9f95c` 的标题部分：节 27px 带下划线（inset shadow，`looks()` 带进缩放副本）、小节 21.5px、下一级 18.5px 与正文同大、最深一级 `--ink-2`；Topic 卡片标题 13.5px 无下划线；未测 zoom 平滑度；记录见 `docs/changes/2026-10-22-reader-heading-scale.md` |

| 2026-10-23 | R18b | feature | `92b8ec3` | 377，OK | 一轮，无阻断；8 条非阻断已修（Aa 字号变化后地图布局不更新——`setType` 重绘、否则清 render key；PDF 并排开关不同步——`openCompare`/`closeCompare` 调 `mapSync`；专注模式地图仍盖在页上——进入时隐藏、退出时恢复且 `mapSync` 拒绝 focus；并排/原段展开时仍显示切换——`updateBar` 一并隐藏；两条测试不能失败（kick 行、`mapSync` 条件、分组 next/prev 与守卫已精确断言）；DEVELOPMENT 的 Topic 标题与分支配色描述；记录误写 `done()` 负责缩放后同步，实为 `rest()`→`updateBar()`） | `fb9f95c` 的地图部分：章节有下级小节时成为一组卡片的行头（`parent`/`top`/`newrow`），缩放条旁可在卡片与思维导图间切换（`textfold.topicview`）；地图在 Topic 静止时覆盖页面，缩放/滚轮/捏合前先隐藏，章节可折叠、主题词点击回到 Key；地图随语言与字号重绘，并排 PDF 与专注模式不显示；未目视点击主题回 Key（预览面板无 rAF）；未测 zoom 平滑度；记录见 `docs/changes/2026-10-22-topic-mind-map.md` |
| 2026-10-23 | R18c | feature | `db85a58` | 378，OK | 一轮，无阻断；8 条非阻断：7 条已修（点击切换、按下方向、焦点选择器、存储键均无断言——已加精确断言；`html[data-hide~="notes"] .paper-head > .lside` 在本 fork 是死选择器——已删；mirror 注释与记录高估了沙箱对边注的作用——已改；DEVELOPMENT 的 `mirrorType` 一句未提 hide——已补），第 5 条“两标签页改类型会互相覆盖”是 `localStorage` 既有行为，记入记录的并发说明；verifier 另在 headless Chrome（1400/800px）确认两个 `.lside` 宿主与 `.side-notes` 都被隐藏、`.side` 空壳高 0、沙箱的 `:host([data-hide~="notes"])` 选择器生效，并用 Node 跑真实解析代码验证 null/旧值/上游形状/损坏 JSON，另确认上游的一行隐藏规则确被层级规则盖过 | 取 `fb9f95c` 的 margins 部分：Aa 菜单新增“页边”一行，AI 问答 / 我的笔记各自显示或隐藏（`html[data-hide]`，随类型存 `localStorage` `textfold.type`，恢复默认清除，`mirrorType` 同步进缩放沙箱）；本 fork 已移除论证链接（`f80969e`），故只有两个边注、不移植第三个，`.side-links` 选择器也不带入；上游一行隐藏规则被 `.u[data-l] > .lside` 与 `.doc[data-level] .chunk > .lside` 盖过（上游同序，疑为潜在缺陷），本 fork 加深选择器并加特异性契约测试；未目视问答边注（`TEXTFOLD_NO_MODELS=1` 无模型回答）、未目视多笔记堆叠与打印；未测 zoom 平滑度；记录见 `docs/changes/2026-10-22-reader-margins.md` |

## 停止条件

- 全部任务 `完成`：停止 loop，汇总 commit、测试数、verifier 结果和未验证项。
- 任务 `阻塞`：测试无法转绿、发现数据丢失/安全问题、删除能力没有替代路径、需要用户改变优先级。
- 发现上一项还有未合并 worktree 或未提交改动：停止，不并行。
- 任何需要 push 的动作：不做；等用户明确要求。
