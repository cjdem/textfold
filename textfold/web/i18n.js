// Interface strings. The interface speaks the language the paper is being read in.
// Every language falls back to English for a missing key.
window.DR_I18N = (() => {
  const ENV = ['Theorem', 'Lemma', 'Proposition', 'Corollary', 'Definition', 'Remark', 'Example', 'Proof', 'Conjecture', 'Claim', 'Assumption', 'Observation', 'Notation'];
  const env = (words) => Object.fromEntries(ENV.map((w, i) => [w, words[i]]));
  const roles = (w) => ({ claim: w[0], gap: w[1], method: w[2], setup: w[3], result: w[4], analysis: w[5], limitation: w[6], context: w[7] });
  const stages = (w) => ({ queued: w[0], fetch: w[1], parse: w[2], ladder: w[3], translate: w[4], done: w[5], zh: w[6] });

  const S = {
    en: {
      tut_open: "How it works", sb_resize: "Drag to change the width. Double-click to reset.", sources_tip: "These sources are read with their own structure: sections, formulas, figures and references stay as the author made them.",
      g_web: "Web pages", web_notext: "This page shows little text without running its scripts, or it needs a sign-in, so it cannot be read here.", web_pdf: "This link is a PDF. Download it and drop it here.", web_blocked: "This site did not let TextFold fetch the page (a sign-in, a paywall, or a block on programs).",
      pdf_reading: "Sending the PDF to MinerU…", file_reading: "Reading the file…", file_large: "This file is larger than 100 MB.", file_bad: "TextFold could not read this file. It may be damaged or protected.", drop_types: "PDF · Word · PowerPoint · Excel · EPUB · HTML · images · Markdown · text", pdf_online: "Found online ({ref}): reading that version, with your PDF as its original.", mineru_needed: "A MinerU API key is needed", mineru_needed_why: "Every PDF is read by MinerU’s Cloud API. Add a key in Settings, then choose the file again; the refused upload was not kept.", mineru_settings: "Add the MinerU key", mineru_connected: "Key saved. PDFs and pictures are read at the API address below.", mineru_not_connected: "No key. PDFs and pictures cannot be read until one is added.", mineru_key: "MinerU API key", mineru_key_note: "Stored in ~/.textfold/settings.json and never sent back to this page.", mineru_key_kept: "A key is saved; leave empty to keep it.", mineru_key_ph: "Paste a MinerU API key", mineru_url: "API address", mineru_url_note: "A MinerU v4-compatible base (not an endpoint). Files and the key are sent here; use https unless the service is on this computer.", mineru_official: "Restore official address", mineru_url_invalid: "The saved API address is not valid; fix it below.", mineru_key_empty: "Paste the key first.", mineru_clear: "Remove key", mineru_clear_q: "Remove the MinerU key? PDFs and pictures will stop reading until another is added.", mineru_privacy_h: "Files leave this computer", mineru_privacy: "PDFs and pictures are uploaded to the API address above for conversion. Use this only for material you are allowed to send there.", st_mineru: "MinerU Cloud API", mineru_bad_key: "That key cannot be saved: use one printable word without spaces.", mineru_bad_url: "That address cannot be used: it must start with http:// or https://, name a host, and carry no query, fragment or sign-in.", busy: "MinerU is busy. Try again when it has finished.", not_now: "Not now", tier: "Conversion", tier_fast: "Fast: seconds; formulas as pictures", tier_accurate: "Accurate: minutes; formulas and tables exact", convert_acc: "Convert accurately", conv_fast_note: "Converted fast: formulas are pictures.", pdf_large: "This PDF is larger than 100 MB.", not_pdf: "This file is not a PDF.", pstages: {"convert": "Converting the PDF", "convert-file": "Converting the file"},
      no_readme: "This repository has no README, or it is private.", github_limit: "GitHub lets a computer that is not signed in ask 60 times an hour. Try again in a while.", g_wiki: "Wikipedia", g_docs: "Documents", pdf_mismatch: "This PDF’s text does not match the paper. Drop another PDF here to replace it.", pdf_open: "Open the PDF on its site", pdf_drop: "Once it is downloaded, drop the PDF here to read beside it.", pdf_pick: "Choose the PDF", pdf_saving: "Saving the PDF…", pdf_bad: "That is not a PDF file.", read_first: "Reading the original meanwhile. The levels appear when they are ready.", compare: "Original", compare_tip: "Read beside the original PDF pages", pdf_loading: "Opening the PDF…", pdf_none: "TextFold could not fetch this paper’s PDF.", pdf_error: "The PDF could not be opened.", stop: "Stop", stopping: "Stopping…", stopped: "Stopped", unfinished: "Unfinished · click to continue", resume: "Continue", close: "Close", md_only: "TextFold opens PDF, Word (DOCX), PowerPoint (PPTX), Excel (XLSX), EPUB, HTML, CSV, image, Markdown and text files.", legacy_format: "TextFold no longer opens new RTF, OpenDocument or old Word, PowerPoint and Excel files. Save the file as DOCX, PPTX, XLSX or PDF, then drop it here.", no_fulltext: "Europe PMC has no open full text of this paper, so it cannot be read here yet.", drop_md: "Drop here", snapshot: "Snapshot of {date}", sources: "Any web page works. Read most fully: arXiv · PubMed Central · bioRxiv · medRxiv · DOI · Wikipedia · GitHub", drop_zone: "Drag one or more files here, or click to choose",
      levels: ['Topic', 'Takeaway', 'Key', 'Brief', 'Full'],
      hint: 'Pinch, Ctrl-scroll, or scroll on this bar to zoom · keys 1–5 · click a paragraph to open it', tagline: "Stretch any article",
      refs: 'References', back: 'Back', figure: 'Figure', table: 'Table',
      roles: roles(['claim', 'gap', 'method', 'setup', 'result', 'analysis', 'limitation', 'context']),
      legend: 'Legend', legend_title: 'Paragraph roles',
      env: env(ENV),
      language: 'Language', read_in: 'Read in', gen_lang: 'Generate', regen: 'Regenerate', stale: 'outdated', generating: 'Generating',
      gaps_filling: "Translating the {n} paragraphs left untranslated", gaps_fill: "Translate the {n} paragraphs left out", gaps_tag: "{n} untranslated",
      fl_adding: "Adding {k} of {n}", fl_waiting: "Waiting for the files already going up…", fl_added: "{n} of {m} files added",
      fl_queue: "They are read, and their levels written, one after another. The sidebar shows each, with a button to stop it.",
      fl_read: "They are read one after another and open as written: their levels need a model.",
      fl_mineru: "{n} need a MinerU key: add one in Settings, then choose them again.",
      fl_skipped: "Not added:", fl_failed: "Failed:", fl_stopped: "Stopped:",
      fl_no_model: "Markdown and text need a model, and none is connected yet.",
      fl_md_large: "Markdown and text files are limited to 12 MB here.",
      fl_retry: "Retry failed",
      fl_duplicate: "already added", fl_too_many: "at most 50 files at a time",
      mineru_limits_h: "Limits", mineru_limits: "MinerU reads up to 600 pages per file; its priority quota is 2,000 pages a day.",
      new_paper: "New", papers: 'Papers', empty: "Nothing here yet", hero: "Stretch any article into five levels, from the full text to a one-screen map.",
      placeholder: "A link to a web page or a paper, or a DOI", generate: 'Generate', settings: "Settings",
      backend_anthropic: 'Anthropic API', backend_openai: 'OpenAI-compatible API',
      api_key: 'API key', model: 'Model', base_url: 'Base URL', save: 'Save', cancel: 'Cancel', test: 'Test', test_ok: 'Connected',
      key_note: 'Keys stay on this computer (~/.textfold).', sdk_note: 'Needs the SDK: pip install anthropic',
      stages: stages(["Waiting", "Fetching the text", "Reading the structure", "Writing the zoom levels", "Translating", "Done", "Making the Simplified Chinese version"]),
      open: 'Open', failed: 'Failed', no_html: 'arXiv has no HTML version of this paper, so it cannot be read here yet.',
      bad_ref: "Paste a link (a web page, a paper) or a DOI.", collapse: 'Collapse', expand: "Library",
      st_model: "Model for generation", st_effort: "Effort", st_default: "default", st_models: "{n} models", st_providers: "API providers", st_add: "Add provider", st_edit: "Edit", st_remove: "Remove", st_fetch: "Fetch models", st_pick: "Models to offer", st_from_td: "ThoughtDAG .env", st_from_env: ".env", st_added: "added here", st_use_td: "Use the keys in ThoughtDAG's .env", st_preset: "Provider", st_name: "Name", st_close: "Close", st_save_provider: "Save provider", st_key_kept: "leave empty to keep the saved key", st_none: "No model available yet", st_current: "Current connection", st_advanced: "Advanced settings", st_or: "OpenRouter in one click",
      sv_title: "Save", sv_export: "Export", sv_export_notes: "Export notes (Markdown)", sv_export_card: "Export reading card (Markdown)", sv_more: "More export options…", sv_what: "What", sv_whole: "The whole text", sv_whole_d: "Every level, with the marks you choose", sv_marks: "Only my marks", sv_marks_d: "The passages you marked, your notes and AI answers, with a link to the source", sv_incl: "Include", sv_hl: "Highlights", sv_notes: "Notes", sv_asks: "AI questions and answers", sv_fmt: "Format", sv_html: "Web page (one HTML file)", sv_pdf_level: "PDF, at {level}", sv_pdf: "PDF", sv_md: "Markdown (Obsidian)", sv_json: "JSON (data)", sv_langs: "Languages", sv_lang_cur: "{lang} only", sv_lang_all: "All {n} languages", sv_lic: "TextFold is only a tool: when you share a file, follow the terms of the original text.", sv_go: "Save", sv_working: "Saving…", sv_failed: "Could not save: {e}", sv_madewith: "Folded with TextFold", sv_para: "The whole paragraph around each mark", sv_pdfin: "The original PDF, to read beside it (a larger file)",
      n_asked_at: "asked at {level}", n_keep: "Keep my highlights", n_keep_tip: "When the text zooms out, the passages you highlighted stay", n_more: "Ask a follow-up…", n_highlight: "Highlight", n_note: "Note", n_ask: "Ask", n_ask_ph: "Ask about this passage…", n_note_ph: "Write a note…", n_thinking: "Thinking…", n_copy: "Copy link", n_copied: "Copied", n_delete: "Delete", n_notes: "Notes", n_export_md: "Export Markdown (Obsidian)", n_export_json: "Export notes data (JSON)", n_failed: "No answer", n_open: "Open in the reader", n_local: "Notes are kept in this browser", n_all: "All", n_del_sure: "Click again to delete", n_export_pdf: "Export PDF: notes only", n_none: "Nothing here yet", home: "Home", del_paper: "Delete", del_confirm: "Delete “{title}”?\n\nIts levels, translations and your {n} notes move to papers/.trash, where you can find them again.", del_busy: "This is still being generated. Delete it when that is done.", n_whole: "The whole paper", n_chat: "Ask the paper", n_chat_ph: "Ask about the whole paper…", n_chat_new: "New chat", n_chat_hint: "Answers come from the paper, with the paragraphs they rest on.", n_try: "Try asking", n_starters: ["What problem does this paper solve, and what is new?", "What is the main evidence for its central claim?", "How does the method work, step by step?", "What are the limitations, and what is left open?", "How does it compare with earlier work?"], n_pstarters: ["Explain this in simpler words", "What is the evidence for this?", "How does this connect to the main claim?"], n_infer: "inference", n_infer_tip: "Not from the paper: the model’s own inference or general knowledge", n_cite_bad: "This citation names no paragraph of the paper", n_demo: "This is a static demo page: there is no model here to answer. Run TextFold on your computer, connect a model, and ask any paper.", n_demo_link: "Get TextFold", n_export_pdf_paper: "Export PDF: the paper at {level}, with notes", or_button: "Connect in one click", or_hint: "Authorize once on OpenRouter: a key is made for you and kept on this computer, with no pasting. Free models work right away.", or_minted: "Authorized. Tick the models to use, then save.", or_failed: "OpenRouter authorization did not finish: {error}. Try again, or paste a key.", free: "free", st_search: "Search models", st_auto: "found here", cn_title: "Connect a model first", cn_sub: "TextFold folds text with a model you already have. Pick one way:", cn_or: "OpenRouter in one click · free models", cn_more: "Other API options", no_model: "No model is connected yet: connect one below.", license: "License", lic_arxiv: "arXiv license: for reading, not for redistribution",
    },
    zh: {
      tut_open: "使用说明", sb_resize: "拖动调整宽度，双击恢复默认", sources_tip: "这些来源有专门的解析：章节、公式、图和参考文献都按原样保留。",
      g_web: "网页", web_notext: "这个网页要运行脚本才显示正文，或者需要登录，所以这里读不了。", web_pdf: "这个链接是 PDF。下载后拖到这里即可。", web_blocked: "这个网站不允许 TextFold 获取页面（需要登录、付费，或拒绝程序访问）。",
      pdf_reading: "正在把 PDF 发给 MinerU…", file_reading: "正在读取文件…", file_large: "这个文件超过 100 MB。", file_bad: "TextFold 读不了这个文件，它可能已损坏或受保护。", drop_types: "PDF · Word · PowerPoint · Excel · EPUB · HTML · 图片 · Markdown · 纯文本", pdf_online: "在网上找到了这篇论文（{ref}）：读网上的版本，你的 PDF 作为它的原文。", mineru_needed: "需要 MinerU API 密钥", mineru_needed_why: "所有 PDF 都由 MinerU 的 Cloud API 读取。请先在设置里添加密钥，再重新选择文件；被拒绝的上传没有留在本机。", mineru_settings: "添加 MinerU 密钥", mineru_connected: "密钥已保存。PDF 和图片会在下面填写的 API 地址读取。", mineru_not_connected: "还没有密钥。添加密钥前，PDF 和图片无法读取。", mineru_key: "MinerU API 密钥", mineru_key_note: "保存在 ~/.textfold/settings.json，不会回传到这个页面。", mineru_key_kept: "已经保存了密钥；留空即可保留。", mineru_key_ph: "粘贴 MinerU API 密钥", mineru_url: "API 地址", mineru_url_note: "MinerU v4 兼容服务的 base 地址（不是具体接口）。文件和密钥会发到这里；如果服务不在本机，请使用 https。", mineru_official: "恢复官方地址", mineru_url_invalid: "保存的 API 地址无效，请在下面修正。", mineru_key_empty: "请先粘贴密钥。", mineru_clear: "移除密钥", mineru_clear_q: "移除 MinerU 密钥？移除后，PDF 和图片将无法读取，直到添加新密钥。", mineru_privacy_h: "文件会离开本机", mineru_privacy: "PDF 和图片会上传到上面填写的 API 地址进行转换。请只提交你有权发送给该服务的材料。", st_mineru: "MinerU Cloud API", mineru_bad_key: "这个密钥无法保存：请使用不含空格的单个可打印字符串。", mineru_bad_url: "这个地址无法使用：必须以 http:// 或 https:// 开头、写明主机名，且不能带查询、片段或登录信息。", busy: "MinerU 正在工作，等它完成后再试。", not_now: "暂不", tier: "转换", tier_fast: "快速：几秒钟，公式是图片", tier_accurate: "精确：几分钟，公式和表格准确", convert_acc: "精确转换", conv_fast_note: "这是快速转换：公式显示为图片。", pdf_large: "这个 PDF 超过 100 MB。", not_pdf: "这不是 PDF 文件。", pstages: {"convert": "转换 PDF", "convert-file": "转换文件"},
      no_readme: "这个仓库没有 README，或者是私有仓库。", github_limit: "GitHub 对未登录的电脑每小时只允许 60 次请求，请稍后再试。", g_wiki: "维基百科", g_docs: "文档", pdf_mismatch: "这份 PDF 的文字和这篇论文对不上。可以把另一个 PDF 拖到这里替换。", pdf_open: "在原网站打开 PDF", pdf_drop: "下载好以后把 PDF 拖到这里，就能对照着读。", pdf_pick: "选择 PDF 文件", pdf_saving: "正在保存 PDF…", pdf_bad: "这不是 PDF 文件。", read_first: "先读原文，缩放层级生成完会自动换上。", compare: "原文", compare_tip: "与原文 PDF 对照阅读", pdf_loading: "正在打开 PDF…", pdf_none: "TextFold 没能取到这篇论文的 PDF。", pdf_error: "PDF 打不开。", stop: "停止", stopping: "正在停止…", stopped: "已停止", unfinished: "未完成 · 点击继续", resume: "继续生成", close: "关闭", md_only: "TextFold 能打开 PDF、Word（DOCX）、PowerPoint（PPTX）、Excel（XLSX）、EPUB、HTML、CSV、图片、Markdown 和纯文本文件。", legacy_format: "TextFold 不再打开新的 RTF、OpenDocument 或旧版 Word、PowerPoint、Excel 文件。请先另存为 DOCX、PPTX、XLSX 或 PDF，再拖到这里。", no_fulltext: "Europe PMC 没有这篇论文的开放全文，暂时无法在这里阅读。", drop_md: "放在这里", snapshot: "{date}的快照", sources: "任意网页都能读；这些来源读得最完整：arXiv · PubMed Central · bioRxiv · medRxiv · DOI · 维基百科 · GitHub", drop_zone: "把一个或多个文件拖到这里，或点击选择",
      levels: ['主题', '要点', '关键句', '简述', '全文'],
      hint: '双指捏合、Ctrl+滚轮，或在这条滑块上直接滚动来缩放 · 数字键 1–5 · 点击段落展开原文', tagline: "展开任何一篇文章",
      refs: '参考文献', back: '返回', figure: '图', table: '表',
      roles: roles(['主张', '缺口', '方法', '设置', '结果', '分析', '局限', '背景']),
      legend: '图例', legend_title: '段落角色',
      env: env(['定理', '引理', '命题', '推论', '定义', '注', '例', '证明', '猜想', '断言', '假设', '观察', '记号']),
      language: '语言', read_in: '阅读语言', gen_lang: '生成', regen: '重新生成', stale: '已过期', generating: '正在生成',
      gaps_filling: "正在补译 {n} 段没翻译的段落", gaps_fill: "补译 {n} 段", gaps_tag: "{n} 段未译",
      fl_adding: "正在添加第 {k} 个，共 {n} 个", fl_waiting: "正在等前面的文件上传完…", fl_added: "{m} 个文件中已添加 {n} 个",
      fl_queue: "它们会一个接一个读取并生成层级。侧栏里能看到每一个的进度，也能停止。",
      fl_read: "它们会一个接一个读取，打开时是原文。生成层级需要先连接模型。",
      fl_mineru: "{n} 个需要 MinerU 密钥：在设置里添加后，重新选择这些文件。",
      fl_skipped: "没有添加：", fl_failed: "失败：", fl_stopped: "已停止：",
      fl_no_model: "Markdown 和纯文本需要模型，现在还没有连接模型。",
      fl_md_large: "Markdown 和纯文本文件在这里最大 12 MB。",
      fl_retry: "重试失败的文件",
      fl_duplicate: "已经在列表里", fl_too_many: "一次最多 50 个文件",
      mineru_limits_h: "额度", mineru_limits: "MinerU 每份文件最多 600 页，优先额度为每天 2,000 页。",
      new_paper: "新建", papers: '论文', empty: "还没有内容", hero: "把任何一篇文章展开成五个层级，从全文到一屏看完的地图。",
      placeholder: "网页或论文的链接，或 DOI", generate: '生成', settings: "设置",
      backend_anthropic: 'Anthropic API', backend_openai: 'OpenAI 兼容接口',
      api_key: 'API key', model: '模型', base_url: 'Base URL', save: '保存', cancel: '取消', test: '测试', test_ok: '已连通',
      key_note: 'Key 只保存在本机（~/.textfold）。', sdk_note: '需要先安装 SDK：pip install anthropic',
      stages: stages(["排队中", "获取原文", "解析结构", "生成缩放层级", "翻译", "完成", "生成简体中文版"]),
      open: '打开', failed: '失败', no_html: 'arXiv 还没有这篇论文的 HTML 版本，暂时无法在这里阅读。',
      bad_ref: "请粘贴一个链接（网页或论文）或 DOI。", collapse: '收起', expand: "列表",
      st_model: "生成用的模型", st_effort: "推理强度", st_default: "默认", st_models: "{n} 个模型", st_providers: "API 供应商", st_add: "添加供应商", st_edit: "编辑", st_remove: "移除", st_fetch: "获取模型列表", st_pick: "要提供的模型", st_from_td: "ThoughtDAG .env", st_from_env: ".env", st_added: "在这里添加", st_use_td: "使用 ThoughtDAG .env 里的 key", st_preset: "供应商", st_name: "名称", st_close: "关闭", st_save_provider: "保存供应商", st_key_kept: "留空则沿用已保存的 key", st_none: "还没有可用的模型", st_current: "当前连接", st_advanced: "高级设置", st_or: "一键连接 OpenRouter",
      sv_title: "保存", sv_export: "导出", sv_export_notes: "导出笔记（Markdown）", sv_export_card: "导出阅读卡（Markdown）", sv_more: "更多导出选项…", sv_what: "内容", sv_whole: "整篇", sv_whole_d: "所有层级，连同你选的标注", sv_marks: "只要我的标注", sv_marks_d: "你标出的原句、笔记和 AI 回答，附原文链接", sv_incl: "包括", sv_hl: "高光", sv_notes: "笔记", sv_asks: "AI 问答", sv_fmt: "格式", sv_html: "网页（单个 HTML 文件）", sv_pdf_level: "PDF（{level}层）", sv_pdf: "PDF", sv_md: "Markdown（Obsidian）", sv_json: "JSON（数据）", sv_langs: "语言", sv_lang_cur: "当前语言（{lang}）", sv_lang_all: "全部 {n} 种语言", sv_lic: "TextFold 只是一个工具。分享文件时，请遵守原文的许可条款。", sv_go: "保存", sv_working: "正在保存…", sv_failed: "保存失败：{e}", sv_madewith: "用 TextFold 折叠", sv_para: "每处标注所在的整段原文", sv_pdfin: "带上原文 PDF，可以在左边对照（文件会大一些）",
      n_asked_at: "在「{level}」层提问", n_keep: "保留我的高光", n_keep_tip: "缩小时，你高光过的句子一直保留", n_more: "继续追问…", n_highlight: "高光", n_note: "笔记", n_ask: "追问", n_ask_ph: "就这段追问…", n_note_ph: "写点笔记…", n_thinking: "思考中…", n_copy: "复制链接", n_copied: "已复制", n_delete: "删除", n_notes: "笔记", n_export_md: "导出 Markdown（Obsidian）", n_export_json: "导出笔记数据（JSON）", n_failed: "没有得到回答", n_open: "在阅读器中打开", n_local: "笔记保存在这个浏览器里", n_all: "全部", n_del_sure: "再点一次删除", n_export_pdf: "导出 PDF：只有笔记", n_none: "这里还没有", home: "主页", del_paper: "删除", del_confirm: "删除《{title}》？\n\n它的各个层级、翻译和你的 {n} 条笔记会移到 papers/.trash，需要时可以从那里找回。", del_busy: "还在生成，等生成完再删除。", n_whole: "整篇论文", n_chat: "问全文", n_chat_ph: "就整篇论文提问…", n_chat_new: "新对话", n_chat_hint: "回答来自论文本身，并标出依据的段落。", n_try: "可以这样问", n_starters: ["这篇论文解决了什么问题，新在哪里？", "核心结论的主要证据是什么？", "方法是怎么一步步做的？", "有哪些局限，还留下了什么问题？", "和以前的工作相比如何？"], n_pstarters: ["用更简单的话解释这段", "这一点的证据是什么？", "这和论文的核心结论有什么关系？"], n_infer: "推断", n_infer_tip: "不是论文里的内容：这是模型自己的推断或常识", n_cite_bad: "这个引用对不上论文里的任何段落", n_demo: "这是静态示例页，没有接入模型，无法回答。在你的电脑上运行 TextFold 并连接一个模型，就能就任何论文提问。", n_demo_link: "获取 TextFold", n_export_pdf_paper: "导出 PDF：{level}层的论文和笔记", or_button: "一键授权", or_hint: "跳转到 OpenRouter 授权一次，自动生成 key 并保存在本机，不用手动粘贴；免费模型开箱可用。", or_minted: "授权成功。勾选要用的模型，然后保存。", or_failed: "OpenRouter 授权没有完成：{error}。可以重试，或手动粘贴 key。", free: "免费", st_search: "搜索模型", st_auto: "自动接入", cn_title: "先连接一个模型", cn_sub: "TextFold 用你已有的模型来折叠文字。选一种方式：", cn_or: "OpenRouter 一键授权 · 有免费模型", cn_more: "其他 API 方式", no_model: "还没有连接模型：先在下面连接一个。", license: "许可", lic_arxiv: "arXiv 默认许可：仅供阅读，不授权转载",
    },
  };
  // a Zotero library (zotero.py): browsed in a dialog, an item read in a click
  const zot = (w) => ({ z_lib: w[0], z_all: w[1], z_search: w[2], z_none: w[3], z_off: w[4], z_api_off: w[5], z_read: w[6], z_open: w[7],
    z_nofile: w[8], no_file: w[9], z_mine: w[10] });
  const Z = {
    en: zot(['Zotero library', 'All items', 'Search titles, authors, years…', 'No items here.', 'Zotero is not running. Open Zotero, then try again.',
      'Turn on Zotero’s local API: Zotero › Settings › Advanced › “Allow other applications on this computer to communicate with Zotero”.',
      'Read', 'Open', 'no file', 'This item has no file in Zotero that TextFold reads, and no DOI whose full text Europe PMC holds.', 'My Library']),
    zh: zot(['Zotero 文献库', '全部条目', '搜索标题、作者、年份…', '这里没有条目。', 'Zotero 没有在运行。打开 Zotero 后再试。',
      '请打开 Zotero 的本地 API：Zotero › 设置 › 高级 ›「允许此计算机上的其他应用程序与 Zotero 通信」。',
      '阅读', '打开', '无文件', '这个条目在 Zotero 里没有 TextFold 能读的文件，也没有 Europe PMC 收录全文的 DOI。', '我的文库']),
  };
  for (const [code, words] of Object.entries(Z)) Object.assign(S[code], words);
  // the app's own updates (desktop-mygo): a newer release, downloaded and installed when the reader says
  const upd = (w) => ({ up_new: w[0], up_get: w[1], up_getting: w[2], up_ready: w[3], up_restart: w[4], up_failed: w[5], up_retry: w[6],
    up_check: w[7], up_latest: w[8], up_check_failed: w[9], up_note: w[10], up_done: w[11], up_whatsnew: w[12], up_star: w[13],
    up_disabled: w[14] });
  const U = {
    en: upd(['TextFold {v} is out.', 'Download', 'Downloading the update… {p}%', 'TextFold {v} is ready.', 'Restart to update',
      'The update could not be downloaded.', 'Try again', 'Check for updates', 'This is the newest version.', 'Could not check for updates.',
      'When it starts, the app asks GitHub whether a newer version is out. Nothing of yours is sent.',
      'TextFold {v} is installed.', 'What’s new', 'Star on GitHub', 'This build does not include signed updates yet.']),
    zh: upd(['TextFold {v} 已发布。', '下载', '正在下载更新… {p}%', 'TextFold {v} 已下载好。', '重启并更新',
      '更新没能下载下来。', '重试', '检查更新', '已经是最新版本。', '没能检查更新。',
      '软件启动时会到 GitHub 查有没有新版本，不发送你的任何内容。',
      'TextFold {v} 已经装好。', '这一版的新内容', '在 GitHub 上点星', '这个版本还没有配置签名更新。']),
  };
  for (const [code, words] of Object.entries(U)) Object.assign(S[code], words);
  // the library in the sidebar: its search, the reader's folders (folders.py), its order by date
  const lib = (w) => ({ sb_search: w[0], sb_nomatch: w[1], f_new: w[2], f_name: w[3], f_rename: w[4], f_delete: w[5], f_del_confirm: w[6],
    f_empty: w[7], f_actions: w[8], f_out: w[9], sort_label: w[10][0], sort_kind: w[10][1], sort_added: w[10][2], sort_opened: w[10][3],
    d_today: w[11], d_week: w[12], d_month: w[13], d_older: w[14] });
  const F = {
    en: lib(['Search titles, authors, ids…', 'Nothing matches.', 'New folder', 'Folder name', 'Rename', 'Delete folder',
      'Delete the folder “{name}”? The documents in it stay in the library.', 'Drag documents here.', 'Folder actions', 'Not in a folder',
      ['Order', 'By kind', 'By date added', 'By last opened'], 'Today', 'Past 7 days', 'Past 30 days', 'Earlier']),
    zh: lib(['搜索标题、作者、编号…', '没有匹配的文档。', '新建文件夹', '文件夹名称', '重命名', '删除文件夹',
      '删除文件夹“{name}”？里面的文档会留在文献库里。', '把文档拖到这里。', '文件夹操作', '不放在文件夹里',
      ['排序', '按类型', '按添加时间', '按最近打开'], '今天', '最近 7 天', '最近 30 天', '更早']),
  };
  for (const [code, words] of Object.entries(F)) Object.assign(S[code], words);
  // the same three, short, side by side under the search
  const BY = {
    en: ['Kind', 'Added', 'Opened'],
    zh: ['类型', '添加时间', '最近打开'],
  };
  for (const [code, [a, b, c]] of Object.entries(BY)) Object.assign(S[code], { by_kind: a, by_added: b, by_opened: c });
  // a document's menu, at a right click on it: the folders it can go into, and out of its own
  const MV = {
    en: ['Move to folder', 'Take out of the folder'],
    zh: ['移到文件夹', '移出文件夹'],
  };
  for (const [code, [a, b]] of Object.entries(MV)) Object.assign(S[code], { f_move_to: a, f_take_out: b });
  // a question's field and its turns: send it, stop it while the model answers, take a turn out of the conversation
  const turn = (w) => ({ n_send: w[0], n_stop: w[1], n_turn_del: w[2], n_turn_del_q: w[3] });
  const Q = {
    en: turn(['Send', 'Stop', 'Delete this question', 'Delete this question and its answer?']),
    zh: turn(['发送', '停止', '删除这一轮', '删除这个问题和它的回答？']),
  };
  for (const [code, words] of Object.entries(Q)) Object.assign(S[code], words);
  // the settings' models: one writes the levels (many calls: a fast one does), one answers questions (the same, unless
  // another is chosen), with how hard it reasons; a test of either that failed
  const EFF = ['auto', 'off', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'ultra'];
  const mods = (w) => ({ st_models_h: w[0], st_gen: w[1], test_bad: w[2], st_ask: w[3], st_same: w[4], st_effort: w[5], sb_ask_with: w[6],
    ...Object.fromEntries(EFF.map((e, i) => [`eff_${e}`, w[7][i]])) });
  const M = {
    en: mods(['Models', 'Default model', 'Failed', 'Answering questions', 'Same as the default', 'Reasoning', 'answers: {m}',
      ['Auto', 'Off', 'Minimal', 'Low', 'Medium', 'High', 'Very high', 'Max', 'Ultra']]),
    zh: mods(['模型', '默认模型', '失败', '回答问题', '与默认相同', '推理强度', '回答用 {m}',
      ['自动', '关闭', '极低', '低', '中', '高', '很高', '极高', '超高']]),
  };
  for (const [code, words] of Object.entries(M)) Object.assign(S[code], words);
  // the reading card (card.js, cards.py): four sections of points, each with the passage that supports it
  const CARD = {
    en: {
      card_title: "Reading card", card_add: "Add to card",
      card_intro: "Keep what this document says in four places, each point tied to the words that support it.",
      card_generate: "Generate reading card", card_manual: "Write it myself", card_lang: "Card language",
      card_draft_lang: "Draft language", card_conflict: "This card was saved elsewhere. It has been reloaded; check your last change.",
      card_load_failed: "Could not open the reading card: {e}", card_too_many: "An item can hold at most six passages.",
      card_reviewed: "Mark as reviewed", card_replace_confirm: "Replace every point and all evidence in this card with the draft?",
      card_discard_confirm: "Discard this draft? The card itself is not changed.",
      card_arm_cancelled: "Link cancelled.", card_mismatch: "Excerpt may no longer match",
      card_no_model: "Automatic generation needs a model. Connect one in Settings; a card written by hand works without one.",
      card_generating: "Generating the reading card", card_generate_failed: "The reading card could not be generated: {e}",
      card_stopped: "Generation stopped. The card is as it was.", card_retry: "Try again",
      card_saving: "Saving…", card_saved: "Saved", card_save_failed: "Could not save: {e}", card_save_retry: "Retry",
      card_unsaved: "Unsaved changes are kept here.",
      card_generated_with: "Drafted with {model} on {at}", card_created: "Created", card_updated: "Updated",
      card_stale: "The document’s own text has changed since this card was made. Review its points and evidence.",
      card_candidate: "New generation, not adopted", card_candidate_partial: "This generation did not finish ({n} parts failed): treat it as incomplete.",
      card_candidate_stale: "The document changed after this draft was made.",
      card_review: "Review draft", card_back: "Back to the card",
      card_replace_all: "Replace the card with this draft", card_merge_all: "Add its new points to the card",
      card_discard: "Discard draft", card_adopt: "Adopt", card_candidate_lang: "Draft language: {lang}",
      card_language_mismatch: "This draft is in another language. Replace the card with it, or make a card in that language first.",
      card_section_empty: "Nothing here yet.", card_add_item: "Add a point",
      card_item_ph: "One point, in your words…", card_state: "Status",
      card_found: "Stated", card_missing: "Not clearly stated", card_na: "Not applicable", card_check: "Needs checking",
      card_verified: "Checked", card_unverified: "Mark as checked",
      card_origin_model: "Model", card_origin_edited: "Model, edited by me", card_origin_user: "Written by me",
      card_recheck: "Document changed: review", card_issue_no_evidence: "No locatable evidence: needs checking",
      card_issue_bad_citation: "The model’s citations could not be located",
      card_evidence: "Evidence", card_no_evidence: "No source linked",
      card_broken: "Target no longer found; the excerpt is kept", card_relink: "Link a passage again",
      card_arm: "Link from the text", card_armed: "Select the passage in the paper, then click “Add to card”.",
      card_pick: "Which point does this passage support?", card_no_items: "Add a point first, then link a passage to it.",
      card_remove_evidence: "Remove this evidence", card_delete_item: "Delete this point",
      card_move_up: "Move up", card_move_down: "Move down", card_export: "Export Markdown",
      card_export_failed: "Could not export: {e}", card_exported: "Markdown saved",
      card_added: "Added to the reading card", card_need_card: "Make a reading card first.",
      card_need_unit: "That selection is not a passage of the original text.",
      card_pick_cancel: "Cancel",
    },
    zh: {
      card_title: "研究阅读卡", card_add: "加入阅读卡",
      card_intro: "把这份文档的要点留在四个栏目里，每条都能回到支撑它的原文。",
      card_generate: "生成阅读卡", card_manual: "手工填写", card_lang: "卡片语言",
      card_draft_lang: "草稿语言", card_conflict: "这张卡在别处保存过，已重新载入；请检查你最后改的地方。",
      card_load_failed: "打不开阅读卡：{e}", card_too_many: "每一条最多关联六段原文。",
      card_reviewed: "标为已复核", card_replace_confirm: "用草稿替换这张卡的全部条目和证据？",
      card_discard_confirm: "丢弃这份草稿？卡片本身不会改变。",
      card_arm_cancelled: "已取消关联。", card_mismatch: "摘录可能已和原文不一致",
      card_no_model: "自动生成需要模型：先在设置里连接一个。手工填写不需要模型。",
      card_generating: "正在生成阅读卡", card_generate_failed: "阅读卡没能生成：{e}",
      card_stopped: "已停止生成，卡片保持原样。", card_retry: "重试",
      card_saving: "保存中…", card_saved: "已保存", card_save_failed: "保存失败：{e}", card_save_retry: "重试",
      card_unsaved: "未保存的修改还留在这里。",
      card_generated_with: "由 {model} 于 {at} 生成", card_created: "创建", card_updated: "更新",
      card_stale: "本卡生成后原文内容已有变化，请复核条目和证据。",
      card_candidate: "新的生成结果（尚未采用）", card_candidate_partial: "这次生成没有完成（{n} 部分失败），内容是未完成的。",
      card_candidate_stale: "生成这份草稿后原文有变化。",
      card_review: "查看草稿", card_back: "回到卡片",
      card_replace_all: "用草稿替换整张卡", card_merge_all: "把新要点加入卡片",
      card_discard: "丢弃草稿", card_adopt: "采用", card_candidate_lang: "草稿语言：{lang}",
      card_language_mismatch: "草稿用的是另一种语言：可以用它替换整张卡，或先生成同语言的卡片。",
      card_section_empty: "这里还没有内容。", card_add_item: "添加一条",
      card_item_ph: "用你自己的话写一条…", card_state: "状态",
      card_found: "有说明", card_missing: "未找到明确说明", card_na: "不适用", card_check: "待核查",
      card_verified: "已核查", card_unverified: "标为已核查",
      card_origin_model: "模型生成", card_origin_edited: "模型生成，我修改过", card_origin_user: "我写的",
      card_recheck: "原文有变化，需复核", card_issue_no_evidence: "没有可定位的证据，待核查",
      card_issue_bad_citation: "模型给出的引用无法定位",
      card_evidence: "证据", card_no_evidence: "未关联原文",
      card_broken: "引用目标已不存在，摘录仍保留", card_relink: "重新关联原文",
      card_arm: "从原文关联", card_armed: "在论文中选中要引用的段落，再点“加入阅读卡”。",
      card_pick: "这段原文支撑哪一条？", card_no_items: "先添加一条，再把原文关联到它。",
      card_remove_evidence: "移除这条证据", card_delete_item: "删除这一条",
      card_move_up: "上移", card_move_down: "下移", card_export: "导出 Markdown",
      card_export_failed: "导出失败：{e}", card_exported: "Markdown 已保存",
      card_added: "已加入阅读卡", card_need_card: "先创建一张阅读卡。",
      card_need_unit: "选中的不是原文段落。", card_pick_cancel: "取消",
    },
  };
  for (const [code, words] of Object.entries(CARD)) Object.assign(S[code], words);
  S.en.up_dev = 'Run from the code, this copy does not update itself.';
  const NATIVE = { en: 'English', zh: '简体中文' };
  const HTML_LANG = { zh: 'zh-CN' };
  // a text that is not a paper (a web page, a README, a PDF, a letter): the questions about it in its words
  const DOCS = {
    "en": { n_chat: "Ask the whole text", n_chat_ph: "Ask about the whole text…", n_chat_hint: "Answers come from the text, with the paragraphs they rest on.", n_whole: "The whole text", n_infer_tip: "Not from the text: the model’s own inference or general knowledge", n_cite_bad: "This citation names no paragraph of the text", n_export_pdf_paper: "Export PDF: the text at {level}, with notes", n_starters: ["What is this about, in a few sentences?", "What are its main points?", "Does it ask me to do or decide anything?", "What is left unclear, or not said?", "Which part matters most, and why?"], n_pstarters: ["Explain this in simpler words", "What does this rest on?", "How does this connect to the main point?"] },
    "zh": { n_chat: "问全文", n_chat_ph: "就全文提问…", n_chat_hint: "回答来自原文，并标出依据的段落。", n_whole: "全文", n_infer_tip: "不是原文里的内容：这是模型自己的推断或常识", n_cite_bad: "这个引用对不上原文里的任何段落", n_export_pdf_paper: "导出 PDF：{level}层的全文和笔记", n_starters: ["这篇讲的是什么？用几句话说。", "主要的几点是什么？", "它要我做什么，或者决定什么吗？", "有哪些地方没说清楚，或者没有提到？", "哪一部分最重要，为什么？"], n_pstarters: ["用更简单的话解释这段", "这一点的依据是什么？", "这和全文的要点有什么关系？"] },
  };
  // text: the document is not a paper, and the questions about it say so
  const t = (lang, text) => ({ ...S.en, ...(S[lang] || {}), ...(text ? { ...DOCS.en, ...(DOCS[lang] || {}) } : {}) });
  // the language a visitor most likely reads, among the ones offered
  function guess() {
    for (const l of navigator.languages || [navigator.language || 'en']) {
      const x = l.toLowerCase();
      if (x.startsWith('zh')) return 'zh';
      const base = x.split('-')[0];
      if (NATIVE[base]) return base;
    }
    return 'en';
  }
  return { t, NATIVE, CODES: Object.keys(NATIVE), htmlLang: (l) => HTML_LANG[l] || l, guess };
})();
