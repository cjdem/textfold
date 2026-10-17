// How TextFold works: a few pages of small pictures, two or three ideas a page. It opens by itself on a first visit to
// the landing, and from "How it works" there and in the reader: window.TFTutorial.open(lang). Its words live here, not in
// i18n.js, so that a page exported on its own (which carries i18n.js) does not carry them too.
(() => {
  'use strict';
  const KEY = 'textfold.tutorialDone';
  const store = { get(k) { try { return localStorage.getItem(k); } catch { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch { /* private window */ } } };
  const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  // the pages, and the ideas on each
  const PAGES = [['link', 'file', 'lang'], ['levels', 'map', 'zoom'], ['voice', 'anchor'], ['original', 'ask', 'notes']];

  // {levels}, {topic}, {brief} and {original} are the reader's own names for them (i18n.js), filled in when shown
  const W = {
    en: {
      title: 'How TextFold works', sub: 'Four short pages: how to read a text that folds.',
      p1: 'Bring a text in', p2: 'Fold and unfold', p3: 'Whose words', p4: 'Read deeper',
      link_t: 'Paste a link', link_d: 'Any web page works. A paper’s link or DOI, Wikipedia and GitHub are read with their sections, formulas and figures.',
      file_t: 'Or drop a file', file_d: 'A PDF, a Word, PowerPoint or Excel file, an EPUB, a picture, Markdown or a .txt. A PDF that names a paper online opens that version. Other PDFs and files are converted on your computer.',
      lang_t: 'Read in your language', lang_d: 'Read in English or Simplified Chinese. The text is translated sentence by sentence, and every formula stays as typeset.',
      levels_t: 'Five levels', levels_d: '{levels}. Each level keeps less of every paragraph, so more of the whole fits on the screen.',
      map_t: 'A map of the text', map_d: 'At {topic}, the text becomes a map of section cards. You see how the sections build on each other before you read any of them.',
      zoom_t: 'Zoom under your fingers', zoom_d: 'Pinch, scroll with Ctrl, press 1 to 5, or drag the level bar. Words that stay slide to their new place. Click a paragraph to open just that one.',
      voice_t: 'Serif is the author', voice_d: 'The author’s words are set in a serif, AI’s in a sans serif. {brief} keeps the author’s own sentences, word for word.',
      anchor_t: 'AI points to its source', anchor_d: 'Every line AI wrote points back to the sentences it rests on. Colors mark each paragraph’s role in the argument.',
      original_t: 'Beside the original', original_d: 'For a paper or a PDF, {original} at the top opens its pages at the left. Each paragraph is marked where it stands on its page.',
      ask_t: 'Ask, and see the evidence', ask_d: 'Select a passage to ask about it, or ask about the whole text. Every answer cites the paragraphs it rests on, one click away.',
      notes_t: 'Notes that zoom with you', notes_d: 'Highlight and write in the margin. What you mark stays as you zoom out. Export gives you your notes as Markdown, and the whole page with them as one file.',
      done: 'Got it', prev: 'Previous page', next: 'Next page', close: 'Close',
      k_levels: 'levels', k_scroll: 'scroll', k_zoom: 'zoom', k_lang: 'next language', k_pages: 'pages', k_close: 'close',
    },
    zh: {
      title: 'TextFold 怎么用', sub: '四页，三分钟，看懂怎样把一份文本折起来读。',
      p1: '带一份文本进来', p2: '折叠与展开', p3: '谁在说话', p4: '读得更深',
      link_t: '粘贴链接', link_d: '任意网页都可以。论文链接或 DOI、维基百科、GitHub 仓库，会连同章节、公式和图一起读进来。',
      file_t: '或者拖入文件', file_d: 'PDF、Word、PowerPoint、Excel、EPUB、图片、Markdown 或 .txt 文件。PDF 如果对应网上的某篇论文，就打开网上的版本。其他 PDF 和文件在你的电脑上转换。',
      lang_t: '用你的语言读', lang_d: '可以读英文或简体中文。逐句翻译，公式保持原样。',
      levels_t: '五个层级', levels_d: '{levels}。每往上一级，每段留下的更少，一屏能看到的整体就更多。',
      map_t: '一张文本地图', map_d: '到了{topic}层，文本变成一张章节卡片的地图。还没读正文，就先看清各章节怎样一步步搭起来。',
      zoom_t: '随手缩放', zoom_d: '双指捏合、按住 Ctrl 滚动、按数字键 1 到 5，或拖动层级条。留下来的词会滑到新位置。点一个段落，只展开这一段。',
      voice_t: '衬线体是作者的原话', voice_d: '作者的原话用衬线体，AI 写的用无衬线体。{brief}层保留的是作者的原句，一字不改。',
      anchor_t: 'AI 的每句话都有出处', anchor_d: 'AI 写的每一行都指回它依据的原句。颜色标出每段在论证中的角色。',
      original_t: '对照原文', original_d: '论文和 PDF 可以点顶部的「{original}」，左边打开原来的页面。每一段都标出它在页上的位置。',
      ask_t: '提问，并看到依据', ask_d: '选中一段文字就能就它提问，也可以就全文提问。每个回答都标出依据的段落，点一下就能跳过去。',
      notes_t: '笔记跟着缩放', notes_d: '高亮，在页边写笔记。缩小时，你标过的内容会留下来。用「导出」可以直接拿到笔记的 Markdown，也可以把整页连同笔记存成一个文件。',
      done: '明白了', prev: '上一页', next: '下一页', close: '关闭',
      k_levels: '层级', k_scroll: '滚动', k_zoom: '缩放', k_lang: '切换语言', k_pages: '翻页', k_close: '关闭',
    },
  };

  // ── the pictures: TextFold's own marks. The author's text in grey lines (and a serif), AI's in the accent (and a sans).
  const L = (x, y, w, c = 'tk-ink') => `<rect class="${c}" x="${x}" y="${y}" width="${w}" height="2.4" rx="1.2"/>`;
  const chip = (x, y, w, t) => `<rect class="tk-card" x="${x}" y="${y}" width="${w}" height="10" rx="5"/><text class="tk-mono" x="${x + w / 2}" y="${y + 7}" text-anchor="middle">${t}</text>`;
  const head = (x1, y1, x2, y2) => {   // a small arrowhead at (x2, y2), pointing from (x1, y1)
    const a = Math.atan2(y2 - y1, x2 - x1), p = (s) => `${(x2 - 4 * Math.cos(a) + s * 2.4 * Math.sin(a)).toFixed(1)} ${(y2 - 4 * Math.sin(a) - s * 2.4 * Math.cos(a)).toFixed(1)}`;
    return `<path class="tk-acc" d="M${x2} ${y2}L${p(1)}L${p(-1)}Z"/>`;
  };
  const file = (x, rot, label, cls) => `<g transform="rotate(${rot} ${x + 9} 18)"><path class="tk-card" d="M${x} 5h13l5 5v20h-18z"/><path class="tk-s-line" d="M${x + 13} 5v5h5"/>`
    + `${L(x + 3, 13, 10, 'tk-line')}${L(x + 3, 17, 12, 'tk-line')}<text class="tk-mono tk-b ${cls}" x="${x + 9}" y="27" text-anchor="middle">${label}</text></g>`;
  const ART = {
    link: chip(11, 8, 24, 'arXiv') + chip(39, 8, 17, 'DOI') + chip(60, 8, 19, 'wiki') + chip(83, 8, 26, 'GitHub')
      + '<rect class="tk-card" x="8" y="29" width="104" height="22" rx="8"/>'
      + '<path class="tk-s-muted" d="M17.5 42.5l4-4M16 40l-1 1a2.4 2.4 0 0 0 3.4 3.4l1-1M23 41l1-1a2.4 2.4 0 0 0-3.4-3.4l-1 1"/>'
      + '<text class="tk-mono" x="29" y="42.3" style="font-size:6.5px">https://…</text>'
      + '<rect class="tk-acc" x="92" y="33" width="16" height="14" rx="5"/><path d="M96.5 40h7M101 37l3 3-3 3" fill="none" stroke="#fff" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>'
      + L(12, 60, 54, 'tk-line') + L(70, 60, 22, 'tk-line'),
    file: file(26, -7, 'PDF', 'tk-red') + file(51, 0, 'MD', 'tk-accent') + file(76, 7, 'TXT', '')
      + '<rect class="tk-soft" x="10" y="38" width="100" height="28" rx="7"/><rect class="tk-s-acc tk-dash" x="10" y="38" width="100" height="28" rx="7"/>'
      + '<path class="tk-s-acc" d="M60 59.5v-13M55.5 50.5L60 46l4.5 4.5"/>',
    lang: '<rect class="tk-card" x="8" y="7" width="44" height="58" rx="5"/><rect class="tk-card" x="68" y="7" width="44" height="58" rx="5"/>'
      + '<text class="tk-mono" x="13" y="16">EN</text><text class="tk-mono" x="73" y="16" style="font-family:var(--sans)">中</text>'
      + '<rect class="tk-soft" x="11" y="34" width="38" height="11" rx="2"/><rect class="tk-soft" x="71" y="34" width="38" height="11" rx="2"/>'
      + L(13, 23, 34) + L(13, 27.5, 24) + L(13, 37, 32, 'tk-ink tk-strong') + L(13, 41.5, 20, 'tk-ink tk-strong') + L(13, 51, 34) + L(13, 55.5, 28)
      + L(73, 23, 30) + L(73, 27.5, 18) + L(73, 37, 34, 'tk-ink tk-strong') + L(73, 41.5, 14, 'tk-ink tk-strong') + L(73, 51, 26) + L(73, 55.5, 32)
      + '<path class="tk-s-line" d="M52 26 C60 26 60 26 68 26M52 53 C60 53 60 53 68 53"/><path class="tk-s-acc" d="M52 39.5 C60 39.5 60 39.5 68 39.5"/>',
    levels: [[6, [14, 13, 14, 12, 14, 9], 'tk-ink'], [3, [14, 12, 10], 'tk-ink'], [2, [14, 11], 'tk-acc tk-ai'], [1, [13], 'tk-acc tk-ai']]
      .map(([n, ws, c], i) => ws.slice(0, n).map((w, j) => L(9 + i * 23, 8 + j * 5, w, c)).join('')).join('')
      + '<rect class="tk-s-acc" x="101" y="7" width="14" height="7" rx="3.5"/>'
      + '<rect class="tk-line" x="11" y="50.5" width="99" height="3" rx="1.5"/><rect class="tk-acc tk-ai" x="11" y="50.5" width="51" height="3" rx="1.5"/>'
      + [16, 39, 62, 85, 108].map((x, i) => `<circle class="${i === 2 ? 'tk-acc' : 'tk-card'}" cx="${x}" cy="52" r="${i === 2 ? 4 : 3}"/><text class="tk-mono${i === 2 ? ' tk-accent tk-b' : ''}" x="${x}" y="66" text-anchor="middle">${i + 1}</text>`).join(''),
    map: [[8, 8, 'gap'], [68, 8, 'method'], [8, 44, 'result'], [68, 44, 'claim']]
      .map(([x, y, r], i) => `<rect class="tk-card" x="${x}" y="${y}" width="44" height="20" rx="4"/><rect style="fill:var(--r-${r})" x="${x}" y="${y + 3}" width="2.5" height="14" rx="1.25"/>`
        + L(x + 7, y + 6, [26, 30, 22, 28][i], 'tk-acc tk-ai') + L(x + 7, y + 11.5, [18, 14, 20, 16][i], 'tk-line')).join('')
      + '<path class="tk-s-acc" d="M52 18H64M30 28V40M90 28V40M52 54H64"/>' + head(52, 18, 67, 18) + head(30, 28, 30, 43) + head(90, 28, 90, 43) + head(52, 54, 67, 54),
    zoom: (() => {
      const rows = [[[8, 10], [20, 14, 1], [36, 8], [46, 12], [60, 10]], [[8, 12], [22, 9], [33, 16, 1], [51, 10], [63, 7]], [[8, 14], [24, 10], [36, 12], [50, 9, 1], [61, 9]], [[8, 10], [20, 16]]];
      let s = '';
      rows.forEach((r, i) => r.forEach(([x, w, keep]) => { s += `<rect class="${keep ? 'tk-acc' : 'tk-line'}" x="${x}" y="${7 + i * 6}" width="${w}" height="3" rx="1.5"/>`; }));
      s += '<rect class="tk-acc" x="8" y="45" width="14" height="3" rx="1.5"/><rect class="tk-acc" x="25" y="45" width="16" height="3" rx="1.5"/><rect class="tk-acc" x="44" y="45" width="9" height="3" rx="1.5"/>';
      s += '<path class="tk-s-acc tk-dash tk-thin" d="M27 10.5 C27 30 15 32 15 43M41 16.5 C41 32 33 34 33 43M54.5 22.5 C54.5 34 48.5 36 48.5 43"/>';
      s += '<rect class="tk-card" x="79" y="8" width="14" height="14" rx="3.5"/><text x="86" y="17.5" text-anchor="middle" class="tk-key" style="font-size:6px">Ctrl</text>'
        + '<text class="tk-mono" x="97" y="17.5" text-anchor="middle">+</text><rect class="tk-card" x="101" y="6" width="12" height="18" rx="6"/><path class="tk-s-muted" d="M107 9.5v4"/>';
      s += [1, 2, 3, 4, 5].map((n, i) => `<rect class="${n === 3 ? 'tk-acc' : 'tk-card'}" x="${8 + i * 14}" y="55" width="11" height="11" rx="3"/><text class="tk-mono${n === 3 ? ' tk-white' : ''}" x="${13.5 + i * 14}" y="62.6" text-anchor="middle">${n}</text>`).join('');
      s += '<path class="tk-s-muted" d="M91 56l4 4.5-4 4.5M109 56l-4 4.5 4 4.5"/>';   // a pinch
      return s;
    })(),
    voice: '<rect class="tk-line" x="59.5" y="10" width="1" height="54"/>'
      + '<text class="tk-serif" x="34" y="31" text-anchor="middle" style="font-size:23px">Aa</text>'
      + '<text class="tk-mono" x="13" y="14" style="font-family:var(--serif);font-size:12px">“</text><text class="tk-mono" x="50" y="14" style="font-family:var(--serif);font-size:12px">”</text>'
      + L(12, 42, 40) + L(12, 47.5, 36) + L(12, 53, 28)
      + '<text class="tk-sans" x="86" y="31" text-anchor="middle" style="font-size:23px;font-weight:550">Aa</text>'
      + '<path class="tk-acc" d="M106 9.5l1.3 3.4 3.4 1.3-3.4 1.3-1.3 3.4-1.3-3.4-3.4-1.3 3.4-1.3z"/>'
      + L(68, 42, 40, 'tk-acc tk-ai') + L(68, 47.5, 26, 'tk-acc tk-ai'),
    anchor: '<rect class="tk-soft" x="8" y="6" width="104" height="14" rx="4"/>' + L(14, 11.8, 70, 'tk-acc') + '<circle class="tk-acc" cx="104" cy="13" r="2.2"/>'
      + '<rect class="tk-card" x="8" y="28" width="104" height="38" rx="4"/><rect style="fill:var(--r-claim)" x="8" y="31" width="2.5" height="32" rx="1.25"/>'
      + '<rect class="tk-soft" x="14" y="38.3" width="84" height="6" rx="1.5"/><rect class="tk-soft" x="14" y="50.3" width="66" height="6" rx="1.5"/>'
      + L(16, 34, 88) + L(16, 40, 80, 'tk-ink tk-strong') + L(16, 46, 90) + L(16, 52, 62, 'tk-ink tk-strong') + L(16, 58, 54)
      + '<path class="tk-s-acc tk-dash tk-thin" d="M34 15.5 C34 28 26 30 24 38.3M70 15.5 C70 34 60 40 58 50.3"/>',
    original: '<rect class="tk-card" x="8" y="6" width="46" height="60" rx="3"/>'
      + [12, 17, 22, 28, 33, 38, 44, 49, 54].map((y, i) => L(13, y, [36, 34, 30, 36, 33, 26, 36, 35, 20][i], 'tk-line')).join('')
      + '<rect class="tk-soft" x="11" y="26" width="40" height="15" rx="2"/><rect class="tk-s-acc" x="11" y="26" width="40" height="15" rx="2"/>'
      + L(13, 28, 36, 'tk-ink') + L(13, 33, 33, 'tk-ink') + L(13, 38, 26, 'tk-ink')
      + '<text class="tk-mono" x="13" y="62.5" style="font-size:5px">PDF · 2/9</text>'
      + '<rect class="tk-card" x="64" y="6" width="48" height="60" rx="3"/><rect class="tk-soft" x="66" y="29" width="44" height="17" rx="2"/>'
      + L(69, 13, 36) + L(69, 18, 30) + L(69, 32, 38, 'tk-ink tk-strong') + L(69, 37, 34, 'tk-ink tk-strong') + L(69, 42, 22, 'tk-ink tk-strong') + L(69, 52, 36) + L(69, 57, 28)
      + '<path class="tk-s-acc" d="M51 33.5 C58 33.5 59 37.5 66 37.5"/>',
    ask: '<rect class="tk-card" x="8" y="6" width="56" height="60" rx="4"/><rect class="tk-hl" x="11" y="21.8" width="50" height="10.4" rx="1.5"/>'
      + [12, 18, 24, 29.5, 36, 42, 48, 54, 60].map((y, i) => L(14, y, [44, 40, 44, 30, 42, 38, 44, 36, 24][i], i === 2 || i === 3 ? 'tk-ink tk-strong' : 'tk-ink')).join('')
      + '<rect class="tk-card" x="72" y="6" width="40" height="15" rx="7.5"/><text class="tk-sans" x="92" y="16.8" text-anchor="middle" style="font-size:9px;font-weight:650">?</text>'
      + '<rect class="tk-soft" x="72" y="27" width="40" height="33" rx="5"/>' + L(77, 33, 30, 'tk-acc tk-ai') + L(77, 38, 24, 'tk-acc tk-ai')
      + '<rect class="tk-card" x="77" y="45" width="14" height="9" rx="4.5"/><text class="tk-mono tk-accent" x="84" y="51.6" text-anchor="middle" style="font-size:5.5px">¶3</text>'
      + '<rect class="tk-card" x="94" y="45" width="14" height="9" rx="4.5"/><text class="tk-mono tk-accent" x="101" y="51.6" text-anchor="middle" style="font-size:5.5px">¶7</text>'
      + '<path class="tk-s-acc tk-dash tk-thin" d="M77 49.5 C68 49.5 70 27 61 27"/>',
    notes: '<rect class="tk-card" x="6" y="7" width="46" height="52" rx="4"/><rect class="tk-hl" x="8.5" y="17.6" width="40" height="11" rx="1.5"/>'
      + [13, 19, 25, 31, 37, 43, 49].map((y, i) => L(10, y, [38, 36, 30, 38, 34, 38, 22][i], i === 1 || i === 2 ? 'tk-ink tk-strong' : 'tk-ink')).join('')
      + '<rect class="tk-note" x="40" y="30" width="22" height="16" rx="2"/>' + L(43, 35, 15, 'tk-warm') + L(43, 40, 10, 'tk-warm')
      + '<path class="tk-s-muted" d="M66 31h9M72 28l3 3-3 3"/>'
      + '<rect class="tk-card" x="79" y="12" width="35" height="30" rx="4"/>' + L(83, 19, 26, 'tk-acc tk-ai') + '<rect class="tk-hl" x="81" y="25.8" width="31" height="6.4" rx="1.5"/>' + L(83, 27.8, 24, 'tk-ink tk-strong') + L(83, 35, 20, 'tk-acc tk-ai')
      + chip(32, 56, 16, 'MD') + chip(51, 56, 18, 'PDF') + chip(72, 56, 22, 'JSON'),
  };

  const CSS = `
.tt-back { position: fixed; inset: 0; z-index: 2000; display: flex; align-items: center; justify-content: center; padding: 24px;
  background: rgba(26, 20, 10, .34); font-family: var(--sans); animation: tt-in .18s var(--ease, ease-out); }
.tt { position: relative; display: flex; flex-direction: column; width: min(960px, 100%); max-height: calc(100vh - 48px); max-height: calc(100dvh - 48px);
  background: var(--card); color: var(--ink); border: 1px solid var(--line); border-radius: 18px; box-shadow: 0 30px 80px -30px rgba(30, 20, 5, .5); outline: none; }
.tt-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; padding: 20px 18px 2px 28px; flex: none; }
.tt-head > div { display: flex; align-items: baseline; flex-wrap: wrap; gap: 2px 12px; min-width: 0; }
.tt-title { margin: 0; font: 650 18px/1.3 var(--sans); letter-spacing: -.01em; color: var(--ink); }
.tt-sub { margin: 0; font-size: 13px; line-height: 1.4; color: var(--muted); }
.tt-x { flex: none; width: 32px; height: 32px; display: grid; place-items: center; border: 0; border-radius: 8px; background: none; color: var(--muted); cursor: pointer; }
.tt-x:hover { background: var(--surface); color: var(--ink); }
.tt-x svg { width: 16px; height: 16px; }
.tt-body { padding: 12px 28px 4px; overflow-y: auto; overscroll-behavior: contain; min-height: 0; }
@media (min-width: 721px) and (min-height: 560px) { .tt-body { min-height: 330px; } }   /* every page the same height: the arrows stay put */
.tt-label { margin: 0 0 12px; font: 650 11.5px/1.4 var(--sans); letter-spacing: .06em; text-transform: uppercase; color: var(--accent); }
.tt-grid { display: grid; grid-template-columns: repeat(var(--n), minmax(0, 1fr)); gap: 14px; }
.tt-card { display: flex; flex-direction: column; min-width: 0; padding: 14px; border-radius: 14px; background: var(--surface); border: 1px solid var(--line-2);
  animation: tt-in .22s var(--ease, ease-out) both; }
.tt-card:nth-child(2) { animation-delay: .04s; } .tt-card:nth-child(3) { animation-delay: .08s; }
.tt-art { flex: none; width: 100%; aspect-ratio: 120 / 72; max-height: 150px; margin-bottom: 12px; border-radius: 10px; background: var(--card); border: 1px solid var(--line-2); overflow: hidden; }
.tt-art svg { display: block; width: 100%; height: 100%; }
.tt-card h3 { margin: 0; font: 650 14px/1.35 var(--sans); color: var(--ink); }
.tt-card p { margin: 6px 0 0; font-size: 13px; line-height: 1.55; color: var(--ink-2); overflow-wrap: anywhere; }
.tt-nav { flex: none; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 28px; }
.tt-arrow { width: 34px; height: 34px; display: grid; place-items: center; border: 1px solid var(--line); border-radius: 9px; background: var(--card); color: var(--muted); cursor: pointer; }
.tt-arrow:hover:not(:disabled) { color: var(--ink); border-color: var(--rule); }
.tt-arrow:disabled { opacity: .3; cursor: default; }
.tt-arrow svg { width: 16px; height: 16px; }
.tt-dots { display: flex; align-items: center; gap: 4px; }
.tt-dots button { width: 22px; height: 22px; padding: 0; border: 0; background: none; cursor: pointer; display: grid; place-items: center; }
.tt-dots i { display: block; width: 8px; height: 8px; border-radius: 99px; background: var(--line); transition: width .2s var(--ease, ease-out), background-color .2s; }
.tt-dots button:hover i { background: var(--faint); }
.tt-dots button[aria-current="step"] { width: 34px; }
.tt-dots button[aria-current="step"] i { width: 24px; background: var(--accent); }
.tt-done { height: 34px; padding: 0 18px; border: 0; border-radius: 9px; background: var(--accent); color: #fff; font: 600 13.5px var(--sans); cursor: pointer; }
.tt-done:hover { background: var(--accent-deep); }
:root:not([data-theme="light"]) .tt-done { color: #fff; }
.tt button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.tt-keys { flex: none; display: flex; flex-wrap: wrap; gap: 4px 16px; padding: 10px 28px 14px; border-top: 1px solid var(--line-2); font-size: 12px; line-height: 20px; color: var(--muted); }
.tt-keys kbd { display: inline-block; min-width: 18px; padding: 0 5px; margin-right: 2px; text-align: center; font: 500 11px/17px var(--mono); color: var(--ink-2);
  background: var(--card); border: 1px solid var(--line); border-bottom-width: 2px; border-radius: 5px; }
.tt-art .tk-card { fill: var(--card); stroke: var(--line); stroke-width: 1; }
.tt-art .tk-line { fill: var(--line); }
.tt-art .tk-ink { fill: var(--ink-2); opacity: .38; }
.tt-art .tk-ink.tk-strong { opacity: .62; }
.tt-art .tk-acc { fill: var(--accent); }
.tt-art .tk-acc.tk-ai { opacity: .6; }
.tt-art .tk-soft { fill: var(--accent-soft); }
.tt-art .tk-hl { fill: var(--hl); opacity: .7; }
.tt-art .tk-warm { fill: var(--warm); opacity: .7; }
.tt-art .tk-note { fill: color-mix(in srgb, var(--warm) 16%, var(--card)); stroke: var(--warm); stroke-width: .8; }
.tt-art .tk-s-acc, .tt-art .tk-s-line, .tt-art .tk-s-muted { fill: none; stroke-width: 1.2; stroke-linecap: round; stroke-linejoin: round; }
.tt-art .tk-s-acc { stroke: var(--accent); }
.tt-art .tk-s-line { stroke: var(--line); }
.tt-art .tk-s-muted { stroke: var(--muted); }
.tt-art .tk-dash { stroke-dasharray: 3 2.5; }
.tt-art .tk-thin { stroke-width: .9; }
.tt-art text { font-family: var(--sans); }
.tt-art .tk-mono { font-family: var(--mono); font-size: 6px; fill: var(--muted); }
.tt-art .tk-b { font-weight: 650; }
.tt-art .tk-red { fill: var(--r-limitation); }
.tt-art .tk-accent { fill: var(--accent); }
.tt-art .tk-white { fill: #fff; }
.tt-art .tk-key { font-size: 8.5px; fill: var(--ink-2); }
.tt-art .tk-serif { font-family: var(--serif); fill: var(--ink); }
.tt-art .tk-sans { font-family: var(--sans); fill: var(--accent); }
@keyframes tt-in { from { opacity: 0; transform: translateY(4px); } }
@media (prefers-reduced-motion: reduce) { .tt-back, .tt-card { animation: none; } .tt-dots i { transition: none; } }
@media (max-width: 720px) {
  .tt-back { padding: 10px; }
  .tt { max-height: calc(100vh - 20px); max-height: calc(100dvh - 20px); border-radius: 16px; }
  .tt-head { padding: 16px 10px 0 18px; }
  .tt-body { padding: 10px 18px 2px; }
  .tt-grid { grid-template-columns: minmax(0, 1fr); gap: 10px; }
  .tt-card { flex-direction: row; align-items: flex-start; gap: 12px; padding: 10px; }
  .tt-art { width: 38%; max-height: none; margin: 0; }
  .tt-card > div { min-width: 0; flex: 1; }
  .tt-nav { padding: 12px 18px; }
  .tt-keys { display: none; }
}`;

  const ICON = {
    x: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8"/></svg>',
    prev: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 3.5L5.5 8l4.5 4.5"/></svg>',
    next: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 3.5L10.5 8 6 12.5"/></svg>',
  };

  let root = null, dialog = null, page = 0, lang = 'en', before = null, overflow = '';

  // the language asked for; else the page's own (<html lang>), as I18N names it
  function pick(l) {
    const codes = Object.keys(W);
    if (l && W[l]) return l;
    const h = (document.documentElement.lang || '').toLowerCase();
    if (h.startsWith('zh')) return 'zh';
    return codes.includes(h.split('-')[0]) ? h.split('-')[0] : 'en';
  }
  function words() {
    const w = { ...W.en, ...W[lang] };
    const T = window.DR_I18N ? window.DR_I18N.t(lang) : {};
    const lv = T.levels || ['Topic', 'Takeaway', 'Key', 'Brief', 'Full'];
    const vars = { levels: lv.slice().reverse().join(' · '), topic: lv[0], brief: lv[3], original: T.compare || 'Original' };
    for (const k of Object.keys(w)) w[k] = w[k].replace(/\{(\w+)\}/g, (m, v) => esc(vars[v] ?? m));
    return w;
  }

  function render() {
    const w = words(), ideas = PAGES[page], last = page === PAGES.length - 1;
    const keepFocus = dialog.contains(document.activeElement) && document.activeElement.closest('.tt-nav');
    dialog.querySelector('.tt-label').textContent = w['p' + (page + 1)];
    const grid = dialog.querySelector('.tt-grid');
    grid.style.setProperty('--n', ideas.length);
    grid.innerHTML = ideas.map((k) => `<div class="tt-card"><div class="tt-art"><svg viewBox="0 0 120 72" aria-hidden="true">${ART[k]}</svg></div>`
      + `<div><h3>${w[k + '_t']}</h3><p>${w[k + '_d']}</p></div></div>`).join('');
    dialog.querySelector('.tt-body').scrollTop = 0;
    const nav = dialog.querySelector('.tt-nav');
    nav.innerHTML = `<button type="button" class="tt-arrow" data-go="-1" aria-label="${esc(w.prev)}" title="${esc(w.prev)}"${page === 0 ? ' disabled' : ''}>${ICON.prev}</button>`
      + `<div class="tt-dots">${PAGES.map((_, i) => `<button type="button" data-page="${i}" aria-label="${i + 1} / ${PAGES.length}"${i === page ? ' aria-current="step"' : ''}><i></i></button>`).join('')}</div>`
      + (last ? `<button type="button" class="tt-done">${esc(w.done)}</button>`
        : `<button type="button" class="tt-arrow" data-go="1" aria-label="${esc(w.next)}" title="${esc(w.next)}">${ICON.next}</button>`);
    if (keepFocus) (nav.querySelector('.tt-done') || nav.querySelector('[data-go="1"]')).focus();
  }

  function go(n) {
    const p = Math.max(0, Math.min(PAGES.length - 1, n));
    if (p === page) return;
    page = p; render();
  }

  // while it is open the page behind takes no keys, no wheel and no pinch: the reader's 1–5, L, Ctrl-scroll and Esc are its own
  function onKey(e) {
    if (!root) return;
    e.stopPropagation();
    if (e.key === 'Escape') { e.preventDefault(); close(); }
    else if (e.key === 'ArrowRight' && !e.metaKey && !e.ctrlKey) { e.preventDefault(); go(page + 1); }
    else if (e.key === 'ArrowLeft' && !e.metaKey && !e.ctrlKey) { e.preventDefault(); go(page - 1); }
    else if (e.key === 'Tab') {   // the focus stays inside
      const f = [...dialog.querySelectorAll('button:not(:disabled)')];
      if (!f.length) return;
      const i = f.indexOf(document.activeElement);
      if (e.shiftKey && i <= 0) { e.preventDefault(); f[f.length - 1].focus(); }
      else if (!e.shiftKey && i === f.length - 1) { e.preventDefault(); f[0].focus(); }
      else if (i < 0) { e.preventDefault(); f[0].focus(); }
    }
  }
  function onWheel(e) {
    if (!root) return;
    e.stopPropagation();
    if (e.ctrlKey || e.metaKey) e.preventDefault();
  }
  function onGesture(e) { if (root) { e.stopPropagation(); e.preventDefault(); } }

  function open(l) {
    lang = pick(l); page = 0;
    if (root) { render(); return; }
    if (!document.getElementById('tt-style')) document.head.append(Object.assign(document.createElement('style'), { id: 'tt-style', textContent: CSS }));
    before = document.activeElement;
    const w = words();
    root = document.createElement('div');
    root.className = 'tt-back';
    root.innerHTML = `<div class="tt" role="dialog" aria-modal="true" aria-labelledby="tt-title" tabindex="-1" lang="${esc(window.DR_I18N ? window.DR_I18N.htmlLang(lang) : lang)}">`
      + `<div class="tt-head"><div><h2 class="tt-title" id="tt-title">${esc(w.title)}</h2><p class="tt-sub">${esc(w.sub)}</p></div>`
      + `<button type="button" class="tt-x" aria-label="${esc(w.close)}" title="${esc(w.close)}">${ICON.x}</button></div>`
      + '<div class="tt-body"><p class="tt-label"></p><div class="tt-grid"></div></div><div class="tt-nav"></div>'
      + `<div class="tt-keys"><span><kbd>1</kbd>–<kbd>5</kbd> ${esc(w.k_levels)}</span><span><kbd>Ctrl</kbd> + ${esc(w.k_scroll)} ${esc(w.k_zoom)}</span>`
      + `<span><kbd>L</kbd> ${esc(w.k_lang)}</span><span><kbd>←</kbd><kbd>→</kbd> ${esc(w.k_pages)}</span><span><kbd>Esc</kbd> ${esc(w.k_close)}</span></div></div>`;
    dialog = root.firstChild;
    root.addEventListener('click', (e) => {
      if (e.target === root) { close(); return; }
      const b = e.target.closest('button');
      if (!b) return;
      if (b.classList.contains('tt-x') || b.classList.contains('tt-done')) close();
      else if (b.dataset.go) go(page + +b.dataset.go);
      else if (b.dataset.page) go(+b.dataset.page);
    });
    for (const ev of ['pointerdown', 'touchstart', 'touchmove', 'mousedown', 'dblclick']) root.addEventListener(ev, (e) => e.stopPropagation());
    addEventListener('keydown', onKey, true);
    addEventListener('wheel', onWheel, { capture: true, passive: false });
    for (const ev of ['gesturestart', 'gesturechange', 'gestureend']) addEventListener(ev, onGesture, true);
    document.body.append(root);
    overflow = document.documentElement.style.overflow;
    document.documentElement.style.overflow = 'hidden';
    render();
    dialog.focus();   // the keys work at once; Tab reaches the buttons
  }

  function close() {
    if (!root) return;
    store.set(KEY, '1');
    removeEventListener('keydown', onKey, true);
    removeEventListener('wheel', onWheel, { capture: true });
    for (const ev of ['gesturestart', 'gesturechange', 'gestureend']) removeEventListener(ev, onGesture, true);
    root.remove(); root = null; dialog = null;
    document.documentElement.style.overflow = overflow;
    if (before && before.focus && before.isConnected) before.focus({ preventScroll: true });
    before = null;
  }

  window.TFTutorial = { open, close, seen: () => !!store.get(KEY), isOpen: () => !!root };
})();
