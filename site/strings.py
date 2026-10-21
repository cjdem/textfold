# The download page's words, in English and Chinese: one key, both languages. build.py puts them in template.html.
# Every claim here is the README's or the app's own (versions, systems, file names); keep them true when either changes.
# Few words: what the page must say and nothing the README says better (it links there).

VERSION = "0.10.7"
SITE = "https://chenxiachan.github.io/textfold/"
REPO = "https://github.com/chenxiachan/textfold"
DL = REPO + "/releases/latest/download/"
FILES = {"win": "TextFold-win-x64-setup.exe"}
LANGS_NATIVE = "English, 简体中文"

S = {
    # the head (search engines, AI answers, shared links)
    "title": ("TextFold · Fold any text, from a map to every word",
              "TextFold · 任何文字，从地图折到每一个字"),
    "description": ("TextFold is a free, open-source reader that folds papers, web pages and project material into five levels, "
                    "from a one-screen map to every word. A Python package, and an app for Windows.",
                    "TextFold 是免费开源的阅读器，把论文、网页和项目材料折成五层，从一屏地图到每一个字。"
                    "既是 Python 包，也有 Windows 软件。"),

    "nav_download": ('Download',
        '下载'),
    "nav_python": ('Python',
        'Python'),
    "nav_docs": ('Docs',
        '文档'),
    "lang_other": ('中文',
        'English'),

    "h1": ("Fold any text, from a one‑screen map to every word.", "任何文字，从一屏地图折到每一个字。"),
    "sub": ("Papers, web pages, and project material. On your computer.",
            "论文、网页和项目材料。都在你自己的电脑上。"),
    "cta_win": ('Download for Windows',
        '下载 Windows 版'),
    "copy": ('Copy',
        '复制'),
    "copied": ('Copied',
        '已复制'),

    "py_h": ('Run it with Python',
        '用 Python 运行'),
    "py_p": ("The same reader as a Python package, on any system with Python 3.9 or newer.",
             "同样的阅读器也有 Python 包，任何装有 Python 3.9 或更新版本的系统都能用。"),
    "py_links": ('<a href="https://github.com/chenxiachan/textfold/blob/main/docs/format.md">The TextFold format</a>',
        '<a href="https://github.com/chenxiachan/textfold/blob/main/docs/format.md">TextFold 格式</a>'),
    "app_p": ('Nothing else to install. It finds Claude Code, Codex or Pi on your computer, or connects a free model in one click.',
        '不用再装别的。它会找到你电脑上的 Claude Code、Codex 或 Pi，也能一键连上免费模型。'),

    "app_meta": (f'Version {VERSION} · Windows 10 and 11, 64-bit · The app updates itself.',
        f'版本 {VERSION} · Windows 10 和 11，64 位 · 软件会自己更新。'),
    "for_you": ('For this computer',
        '适合这台电脑'),

    "faq_h": ('Questions',
        '常见问题'),
    "q1": ("What is TextFold?", "TextFold 是什么？"),
    "a1": ("A free, open-source reader and toolkit that folds any text into five levels, from a map of its sections to every word.",
           "免费开源的阅读器和工具包，把任何文字折成五层，从章节地图到每一个字。"),
    "q2": ("Is it free?", "免费吗？"),
    "a2": ("Yes, under the Apache License 2.0. The levels are written by a model you connect, so any cost is that model's.",
           "免费，Apache 2.0 许可证。各层由你连接的模型来写，如果有费用，也是那个模型的。"),
    "q3": ("How is it different from a summary?", "和摘要有什么不同？"),
    "a3": ("The text stays. The two finest levels are the author's own sentences, and every line a model writes points back to them.",
           "原文一直都在。最细的两层就是作者的原句，模型写的每一行都指回这些原句。"),
    "q4": ("What leaves my computer?", "什么内容会离开我的电脑？"),
    "a4": ("Your library stays on your computer. Text goes to the model you connect; every PDF and picture goes to MinerU's Cloud API for conversion, and the page tells you before files are sent.",
           "文献库留在你自己的电脑上。文字会发送给你连接的模型；每个 PDF 和图片都会交给 MinerU Cloud API 转换，页面会在发送文件前说明。"),

    "foot_readme": ('README',
        'README'),
    "foot_format": ('The format',
        '格式'),
    "foot_releases": ('Releases',
        '所有版本'),
    "notes": ('Release notes',
        '更新说明'),
    "cta_py": ('Run it with Python',
        '用 Python 运行'),
    "foot_license": ('Apache 2.0 © 2026 Xia Chen',
        'Apache 2.0 © 2026 Xia Chen'),

    "hero_note": ('Free and open source · No account · Formerly PaperFold',
        '免费开源 · 不用注册 · 原名 PaperFold'),
    "cta_win_sub": ('64-bit · installer',
        '64 位 · 安装程序'),
    "cta_py_sub": ('python3 -m pip install textfold',
        'python3 -m pip install textfold'),

    "dl_h": ('Get TextFold',
        '获取 TextFold'),
    "apps_h": ('Or read in the app',
        '或者，用软件来读'),
    "dl_win_os": ('Windows',
        'Windows'),
    "dl_win_for": ('Windows 10 and 11, 64-bit',
        'Windows 10 和 11，64 位'),
    "dl_win_note": ('Not signed yet: the first time, choose More info, then Run anyway.',
        '暂未签名：第一次打开时点“更多信息”，再点“仍要运行”。'),
    "dl_btn_exe": ('Download installer',
        '下载安装程序'),
    "readme_line": ('The <a href="https://github.com/chenxiachan/textfold#readme">README</a> has the rest: every source it reads, every key, every model.',
        '其余的都在 <a href="https://github.com/chenxiachan/textfold/blob/main/README.zh-CN.md">README</a> 里：能读的所有来源、所有快捷键、所有模型。'),
    # the opening's typed line (ascii.rest's typewriter): what can be folded
    "typer_prefix": ("fold ", "折叠"),
    "logo_alt": ("Three paragraphs folding to their points, fold any text, keep the point, unfold, the rest gathered into the bars of TextFold's mark, and opening out again",
        "三段文字折到各自的要点（fold any text、keep the point、unfold），其余收进 TextFold 标志的三条横条，再展开回来"),
}

FAQ = [(f"q{i}", f"a{i}") for i in range(1, 5)]
TYPED = {"en": ["a paper.", "a web page.", "a PDF.", "a Word file.", "project material."],
         "zh": ["一篇论文。", "一个网页。", "一份 PDF。", "一份 Word 文档。", "一份项目材料。"]}
