<div align="center">

<img src="https://raw.githubusercontent.com/cjdem/textfold/main/docs/assets/logo.svg" width="72" alt="TextFold">

# TextFold

**折叠任何文字，从一屏地图到每一个字**

<sub>原名 PaperFold</sub>

> **这是一个 fork。** TextFold 由 Xia Chen 创建。这个 fork 由 cjdem 维护，与原项目没有隶属
> 或背书关系。整个项目只支持 Windows：桌面版用 MyGo 取代 Electron 外壳，桌面版和 Python 包
> 的 PDF、图片一律交给 MinerU Cloud API，本机不再安装 PDF 引擎。原归属和完整修改说明见 [NOTICE](NOTICE)。

<img alt="Python 3.9+" src="https://img.shields.io/badge/python-3.9%2B-6B5CE7?style=flat-square">
<img alt="在你的电脑上运行" src="https://img.shields.io/badge/runs-on_your_computer-E08A3C?style=flat-square">
<a href="LICENSE"><img alt="Apache 2.0 许可证" src="https://img.shields.io/badge/license-Apache_2.0-6B5CE7?style=flat-square"></a>

[English](README.md) · **简体中文**

**粘贴链接：** 任意网页 · arXiv · PubMed Central · bioRxiv · medRxiv · 维基百科 · GitHub<br>
**拖入文件：** PDF · Word · PowerPoint · Excel · EPUB · HTML · CSV · 图片 · Markdown · 纯文本

**[下载软件 ↓](#开始使用)** · [最新 ↓](#最新)

<br>

<img src="https://raw.githubusercontent.com/cjdem/textfold/main/docs/assets/zoom-zh.gif" width="880" alt="一篇论文从全文折叠成章节地图，再展开回来">

</div>

## 读长文，脑子里少装一点

自由选择你需要的文字信息层级，降低认知负担。

| | 层级 | 每一段变成 | 谁的话 |
|:-:|---|---|---|
| **1** | **全文** | 原样的段落 | 作者 |
| **2** | **简述** | 一到三句关键原句，一字不改 | 作者 |
| **3** | **关键句** | 这一段的要点和理由 | AI，依据是简述里那几句 |
| **4** | **要点** | 一行，挂在本节的主线上 | AI |
| **5** | **主题** | 几个词；整篇变成一张章节卡片地图 | AI |

## 你会得到

- **词会移动，不会被换掉。** 缩放时，留下的词滑到新的位置，其余的在周围淡出。
- **缩放跟着手指走。** 可以停在半路、往回退，也可以只展开一段。

- **对照原文。** 论文或 PDF 的原页可以放在旁边，读到哪一段，就标出它在原页上的位置。
- **针对内容，结构化地问 AI。** 选中一段，或者就全文提问。回答先给结论，再列依据，每条依据都标出原文段落，点一下就到。
- **笔记跟着缩放。** 在页边高光、写笔记，缩小时标过的内容依然在，也会和整页一起保存。
- **留得下来的阅读卡。** 研究问题、方法、实验设置和结果四栏，每条都能改，也都连着支撑它的原文；重新生成只会放在旁边当候选，不会盖掉你写的内容。

- **用你的语言读。** 英文和简体中文，逐句翻译，公式保持原样。

- **你的文献库，井井有条。** 用 Ctrl+K 搜索；建文件夹整理文档，拖进去或者右键移进去；按类型、添加时间或最近打开排序。

<table>
<tr>
<td width="50%"><img src="https://raw.githubusercontent.com/cjdem/textfold/main/docs/assets/notes.png" alt="全文里的高光和页边笔记"></td>
<td width="50%"><img src="https://raw.githubusercontent.com/cjdem/textfold/main/docs/assets/keep.png" alt="高光过的句子在要点层被保留"></td>
</tr>
<tr>
<td align="center"><sub>在全文里高光、在页边写笔记……</sub></td>
<td align="center"><sub>……缩小时，标过的内容依然在。</sub></td>
</tr>
</table>

## 直接读你的 Zotero

点拖放框下面的 **Zotero 文献库**，你的文献库就按 Zotero 里的样子出现：分类、群组文献库、搜索都在。任何条目点 **阅读** 就能打开。

- **arXiv 上有的条目**，从 arXiv 读。其他条目读它的 PDF，PDF 放在旁边对照；没有 PDF 就读它附带的 EPUB、保存的网页或 Word（DOCX）文件。只有 DOI 的条目，从 Europe PMC 读。旧版 Word、PowerPoint、Excel 附件不再导入：条目先试 DOI，再提示该格式不再支持。
- **你在 Zotero 里填的信息都保留**：标题、作者和 citekey。
- **一切都在你的电脑上。** TextFold 读的是你已经在用的 Zotero 应用，和引文插件的方式一样：不需要账号和密钥，不向 Zotero 的服务器发送任何东西，也不会改动你的文献库。

打开方法：在 Zotero 7 里勾选 **设置 › 高级 › 允许此计算机上的其他应用程序与 Zotero 通信**。

## 开始使用

**[下载软件](https://cjdem.github.io/textfold/zh.html#download)**，只有 Windows 版。需要的东西都在里面，包括 Python；唯一例外是 WebView2，Windows 11 自带，Windows 10 可能会先提示安装。

也可以从本 fork 安装 Python 包，在 Windows 上使用：

```bash
python -m pip install git+https://github.com/cjdem/textfold
python -m textfold serve
```

在浏览器里打开 `http://localhost:3017`。第一次使用先[连接一个模型](#连接模型)，然后粘贴链接或拖入文件，再选择语言。需要在 Windows 上使用 Python 3.9 或更新版本。

| 粘贴或拖入 | TextFold 读到的 |
|---|---|
| 论文的链接或 DOI：arXiv、PubMed Central、bioRxiv、medRxiv | 网站上结构化的正文（arXiv 论文没有 HTML 版本时读它的 PDF；其他 DOI 要在 Europe PMC 有开放全文） |
| 其他任何网页 | 它的正文，去掉菜单、广告，以及网页对读者隐藏的文字 |
| 维基百科条目、GitHub 仓库 | 条目；README，连同里面的图 |
| PDF | 正文和结构一律交给 MinerU Cloud API 解析；原 PDF 仍留在旁边供原文对照 |
| Word（DOCX）、PowerPoint（PPTX）、Excel（XLSX）文件，CSV、EPUB、保存的网页 | 文档本身，标题、表格、图片和公式都保留：常见 Word、Excel、CSV、EPUB 和 HTML 在本机读取 |
| 图片 | 由 MinerU Cloud API 识别出的文字 |
| Zotero 文献库里的条目 | 有 arXiv 版本就读 arXiv，否则读它的 PDF 或其他附件，再没有就按 DOI 读。[直接读你的 Zotero ↑](#直接读你的-zotero) |
| Markdown 或纯文本文件 | 原样的文件 |

所有 PDF 和图片都会上传到 MinerU Cloud API。密钥在 **设置 › 高级 › MinerU API** 中填写，保存在 `~/.textfold/settings.json`，不会回传到页面。本机不再安装 PDF 引擎，也没有离线 PDF 回退。常见的 Word、PowerPoint、Excel、EPUB、CSV 和 HTML 仍在本机读取。

新的 RTF、OpenDocument（.odt、.ods、.odp）和旧版 Word、PowerPoint、Excel 文件（.doc、.ppt、.xls）不再接受导入：请先另存为 DOCX、PPTX、XLSX 或 PDF。已经在文库里的文档照常打开，已生成的层也保留。

本地 MinerU 引擎移除后，新的 OFD 和 TIFF 文件也不再接受；已经在文库里的文档仍可阅读。

读过的文档保存在系统存放应用数据的文件夹里，和桌面 App 共用。

<details>
<summary>也可以直接从代码运行</summary>

```bash
git clone https://github.com/cjdem/textfold.git
cd textfold
python -m pip install -r requirements.txt
python -m textfold serve
```

这样文档保存在代码目录里。

</details>

## 连接模型

TextFold 通过 API 供应商发送模型请求，不会扫描或运行 Claude Code、Codex、Pi 命令行 Agent。如果你已经在电脑上运行可选的 [Magpie 网关](https://github.com/yetone/magpie)，TextFold 会从 `http://127.0.0.1:3425/v1/models` 动态读取它提供的模型。Magpie 是独立的外部服务，TextFold 不会安装它。你明确选择且当前可用的模型会继续作为默认；否则 Magpie 可用时，默认选择它列出的第一个模型。

| 你有 | 怎么做 |
|---|---|
| 正在运行的本地 Magpie | 不用设置。TextFold 会连接它的 OpenAI 兼容 API，并列出 Magpie 返回的模型。 |
| 还没有模型 | 点 **OpenRouter 一键授权**。授权一次，免费模型马上可用。 |
| 一个 API key | **设置 › 高级 › 添加供应商**：Anthropic、OpenAI、DeepSeek、通义千问、智谱 GLM、Kimi、MiniMax、Google、Ollama，或任何 OpenAI 兼容接口。 |

Magpie 不可用时，TextFold 会使用其他可用供应商。回答问题可以用比生成层级更强的模型：**设置 › 高级 › 回答问题**，还可以选推理强度。

## 阅读时的操作

| 操作 | 作用 |
|---|---|
| 双指捏合，或 Ctrl 加滚轮 | 围绕鼠标所在处缩放 |
| `1` 到 `5` | 跳到某一层 |
| 点击某一段 | 只展开这一段 |
| 点击图片 | 放大查看 |
| 顶部的 **原文** | 对照原文 PDF 阅读 |
| 顶部的 **导出** | 把笔记或阅读卡存成 Markdown；更多格式和整页在对话框里 |
| 顶部的 **阅读卡** | 留下一篇论文回答的四个问题，每条都能回到原文 |
| 选中文字 | 高光、写笔记或追问 |
| 右下角 **问全文** | 就整篇提问 |
| `L` | 切换到下一种语言 |
| `Ctrl+K` 或 `/` | 搜索文献库 |

## 导出

阅读页顶部的 **导出** 直接给出两样最常用的文件：笔记的 Markdown，和阅读卡的 Markdown。**更多导出选项…** 打开保存对话框：把一页存成一个 HTML 文件，不需要服务器，在哪里都能打开（各个层级、你选的标注，还可以带上原文 PDF 在左边对照）；也可以只存你的标注，存成网页、PDF、Obsidian 用的 Markdown 或 JSON。

TextFold 只是一个工具，它的许可证只管代码。分享文件时，请遵守原文的许可条款，它标在每篇的标题下方。

## 最新

> 这个 fork 在 10 月 21 日之前的条目是原项目的历史；本 fork 的改动在 [docs/changes/](docs/changes/)。
> 原项目的 macOS 版不属于本 fork。

- **2026 年 10 月 22 日：移除 ChatGPT 订阅入口。** TextFold 不再运行本地桥，也不再使用 ChatGPT 订阅；请改用 API key、OpenRouter 或 Magpie 网关。
- **2026 年 10 月 18 日：每篇论文一张阅读卡。** 阅读页顶部的 **阅读卡** 把研究问题与贡献、方法与前提、数据与实验设置、结果与局限放在一起，条目都能改，也都回到原文；重新生成先存为候选，卡片可导出 Markdown。
- **2026 年 10 月 21 日：PDF 只走 MinerU Cloud API。** 每个 PDF 都直接交给 MinerU，不再先读本地文字，也不先查找在线版本。约 3.4 GB 的本地引擎和离线 PDF 路径已经删除。请先在设置里填写密钥；PDF 和图片会离开电脑，交给 MinerU 转换。
- **2026 年 10 月 17 日：MinerU 的服务器读你的文件。** 在 `~/.textfold/settings.json` 里写上 `mineru_api_key`，PDF、Word/PowerPoint/Excel 文件、HTML 和图片就交给 MinerU 的云 API 读：不用装 3.4 GB 的引擎，文件会离开你的电脑。
- **2026 年 10 月 17 日：英文文档默认带上简体中文版。** App 里打开一篇英文文档，会在同一次生成的最后顺便做出简体中文版，不用再请求一次就能读中文。
- **2026 年 10 月 15 日：不装 PDF 引擎也能读 PDF。** 自带文字的 PDF（大多数论文都是）直接打开，图从原页上裁出来；只有扫描件还需要 PDF 引擎。没有 HTML 版本的 arXiv 论文改读它的 PDF。感谢 [@sylvainHellin](https://github.com/sylvainHellin)。
- **2026 年 10 月 15 日：你的文献库和你的提问。** 文献库可以搜索、建文件夹，按添加时间或最近打开排序。提问有了发送和停止键，对话里任何一轮都可以删掉，回答问题还可以用比生成层级更强的模型。感谢 [@suhyungJang](https://github.com/suhyungJang)。
- **2026 年 10 月 14 日：Mac 和 Windows 软件。** 下载 TextFold 的 macOS 版（Apple 芯片或 Intel，已签名并经苹果公证）或 Windows 版，需要的东西都在里面。桌面版会在你同意后自行更新。[下载 ↓](#开始使用)

<details>
<summary>更早</summary>

- **2026 年 10 月 14 日：直接读你的 Zotero 文献库。** 拖放框下面的 **Zotero 文献库** 按 Zotero 里的样子列出你的文献库和分类，任何条目点一下就能打开：arXiv 上有就读 arXiv，没有就读它自己的 PDF。感谢 [@adalach](https://github.com/adalach)。[直接读你的 Zotero ↑](#直接读你的-zotero)
- **2026 年 10 月 14 日：读 arXiv 页面更安全了。** 页面里可能运行脚本的部分，会在阅读器显示之前去掉，图都保持原样。感谢 [@neil-patel77](https://github.com/neil-patel77)。
- **2026 年 10 月 13 日：把一页存成一个文件。** 阅读页顶部的 **导出** 打开导出菜单；**更多导出选项…** 打开保存对话框：把整页存成一个 HTML 文件，可以带上标注和原文 PDF；也可以只存标注。[导出 ↓](#导出)
- **2026 年 10 月 13 日：Word、PowerPoint、Excel、电子书等文件。** 拖入 Word、PowerPoint、Excel 文件，或 CSV、EPUB、保存的网页，马上就能打开，公式也在，不用另装任何东西。
- **2026 年 10 月 13 日：完整的图，和使用说明。** PDF 引擎拆成碎块的图，现在从原页上整幅裁出来。第一次打开会弹出一份简短的使用说明，之后可以从 **使用说明** 再打开。
- **2026 年 10 月 9 日：PaperFold 改名为 TextFold。** 还是同一个阅读器，新名字涵盖它能折叠的一切：论文、网页、PDF、README。旧仓库的链接会自动跳到这里，设置也会自动搬过来。
- **2026 年 10 月 9 日：任意网页和 PDF。** 粘贴任何网页的链接，就能在五个层级上读它的正文，网页对读者隐藏的文字会被去掉。拖入一个 PDF：如果它是一篇网上能读到的论文，就打开网上的版本，你的 PDF 放在旁边对照；其他 PDF 在你的电脑上转换。
- **2026 年 10 月 8 日：读任何 GitHub README。** 粘贴仓库链接，就能在五个层级上读它的 README，logo、徽章和动图都和 GitHub 上一样。
- **2026 年 10 月 8 日：对照原文读。** 论文页顶部的 **原文** 会在左边打开它的 PDF，读到哪一段，就标出它在原页上的位置。新论文解析完就能打开，缩放层级在后台生成。
- **2026 年 10 月 6 日：不只读 arXiv。** PubMed Central、bioRxiv、medRxiv、任何语言的维基百科，以及你自己的 Markdown 文件。

</details>

<br>

## 原项目贡献者

<a href="https://github.com/neil-patel77" title="@neil-patel77"><img src="https://github.com/neil-patel77.png?size=80" width="40" height="40" alt="@neil-patel77" /></a>
<a href="https://github.com/adalach" title="@adalach"><img src="https://github.com/adalach.png?size=80" width="40" height="40" alt="@adalach" /></a>
<a href="https://github.com/suhyungJang" title="@suhyungJang"><img src="https://github.com/suhyungJang.png?size=80" width="40" height="40" alt="@suhyungJang" /></a>
<a href="https://github.com/sylvainHellin" title="@sylvainHellin"><img src="https://github.com/sylvainHellin.png?size=80" width="40" height="40" alt="@sylvainHellin" /></a>
<a href="https://github.com/jlamweil" title="@jlamweil"><img src="https://github.com/jlamweil.png?size=80" width="40" height="40" alt="@jlamweil" /></a>

本 fork 由 [cjdem](https://github.com/cjdem) 维护。欢迎贡献：先看 [CONTRIBUTING.md](CONTRIBUTING.md)。

<br>

<div align="center">

**如果 TextFold 让阅读轻松了一些，点个 ⭐ [star](https://github.com/cjdem/textfold)，让更多人看到它。**

</div>

---

<div align="center">

<sub>TextFold 建立在这些开源项目之上：[trafilatura](https://github.com/adbar/trafilatura) 从网页中找出正文，[PDFium](https://pdfium.googlesource.com/pdfium/)（经由 [pypdfium2](https://github.com/pypdfium2-team/pypdfium2)）从原页裁出图，[MinerU](https://github.com/opendatalab/MinerU) 的 Cloud API 读取每个 PDF，[mammoth](https://github.com/mwilliamson/python-mammoth) 读取 Word 文件，[PDF.js](https://github.com/mozilla/pdf.js) 显示 PDF，[KaTeX](https://katex.org) 排版公式。桌面外壳使用 [MyGo](https://github.com/egoist/mygo)。感谢它们的作者。</sub>

[Apache 2.0](LICENSE) © 2026 Xia Chen；fork 改动 © 2026 cjdem · [开发文档](docs/DEVELOPMENT.md) · [格式](docs/format.md) · [参与贡献](CONTRIBUTING.md) · [安全](SECURITY.md) · [反馈](https://github.com/cjdem/textfold/issues)

</div>
