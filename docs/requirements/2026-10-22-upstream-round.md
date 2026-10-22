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
| R4 | 待做 | optimize | 只支持流式的 API 服务 | `8e7569b` | 无 | 中 |
| R5 | 待做 | optimize | 模型回复的多种 JSON 形状 | `09e9d37` | 无 | 中 |
| R6 | 待做 | optimize | `TEXTFOLD_NO_MODELS` 下不调用模型 | `1761a95` | 无 | 小 |
| R7 | 待做 | optimize | EPUB 章节先解码再解析 | `13d7794` | 无 | 小 |
| R8 | 待做 | optimize | 翻译漏段重试（只取 `d457cfa` 的翻译部分） | `d457cfa` | 无 | 中 |
| R9 | 待做 | optimize | 应用 payload 带 Anthropic SDK | `f260244` | 无 | 小 |
| R10 | 待做 | feature | 多文件导入：逐文件队列，不用 MinerU batch | `523e5f4` | R1–R9 | 中 |
| R11 | 待做 | feature | 可配置 MinerU v4 base URL，默认官方 | fork-specific | R10 后或并行 | 小 |
| R12 | 待做 | feature | self-hosted V1 adapter（条件项） | fork-specific | R11；仅确有自部署时 | 大 |
| R13 | 待做 | feature | 中文 Brief 句子切分 | `770fb08` | R4/R5 之后 | 中 |
| R14 | 待做 | feature | 中文五级折叠 | `4897e24` | R13 | 大 |
| R15 | 待做 | optimize | CJK 规则只作用于中日文 | `6e2cada` | R14 | 中 |
| R16 | 待做 | feature | Aa 菜单 + 缩放沙箱 font/width | `f76eb4d` + `c38804e` | R14/R15 之后 | 中 |
| R17 | 待做 | feature | 主题、行距、阅读位置、专注模式 | `e5bd668` + `a670e57` + `920a270` | R16 | 中 |
| R18 | 待做 | feature | 标题层级、Topic 分组/思维导图、margins | `fb9f95c` | R16/R17；可拆三次 | 大 |
| R19 | 待做 | feature | 侧栏固定 | `b977bba` | R16/R18 | 中 |
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
- R16→R17→R18→R19 是阅读器依赖链；R18 可拆成三次。
- R20/R21 独立；R22/R23 是可选，审核时可删。
- 触及阅读器的任务在记录里写“zoom 平滑度未测”。

## 执行记录

| 日期 | 任务 | 模式 | 本地 commit | 测试 | verifier | 备注 |
|---|---|---|---|---|---|---|
| 2026-10-22 | R0 | optimize | `b4140d8` | 206，OK | 无阻断发现；1 处 UI 缺陷、3 处测试缺口已修 | 移除 ChatGPT 本地桥，OpenRouter 移到 `textfold/openrouter.py`；失去产品内订阅入口；zoom 平滑度未测 |
| 2026-10-22 | R1 | optimize | `0507bda` | 211，OK | 无阻断发现；测试观察面、死代码与 docstring 已补 | Host 校验在 `do_GET`/`do_POST` 路由前，其他名字 421；`localhost.`、`127.0.0.2` 等按设计拒绝；不涉及阅读器 |
| 2026-10-22 | R2 | optimize | `4f8eff6` | 214，OK | 无阻断发现；1 个数据安全问题、1 个钩子编码问题、若干措辞/测试已修 | 所有文本 I/O 显式 UTF-8；命令行导入支持 GBK/BOM/CRLF；GBK 的 library/zotero 不再被静默清空；旧文件迁移留给 R3 |
| 2026-10-22 | R3 | optimize | `02bc0e2` | 222，OK | 两轮：第一轮推翻“读时写回”（比较与替换非原子，会丢并发保存），第二轮修完记录/测试/文档的 7 处问题；无阻断发现 | 与计划不同：读只解码不写（GBK 文件保持原样，下一次保存写 UTF-8），两边都无法解码的文件报错而非用替换字符后保存；`store.codepage()` 在 3.9/3.10 用 GetACP，不再受 UTF-8 模式影响；`zotero.apply` 改临时文件+替换；未触及阅读器，zoom 平滑度未测 |

## 停止条件

- 全部任务 `完成`：停止 loop，汇总 commit、测试数、verifier 结果和未验证项。
- 任务 `阻塞`：测试无法转绿、发现数据丢失/安全问题、删除能力没有替代路径、需要用户改变优先级。
- 发现上一项还有未合并 worktree 或未提交改动：停止，不并行。
- 任何需要 push 的动作：不做；等用户明确要求。
