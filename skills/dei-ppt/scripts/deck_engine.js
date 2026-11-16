// dei-ppt 主题版引擎（pptxgenjs）：按一张主题图（海报）适配配色和背景，出可编辑、带讲稿、带分组和入场动画的 PPTX。
//
// 内容文件里：
//   const E = require(process.env.DEI_PPT_ENGINE);          // build.py 会设置这个环境变量
//   const D = E.createDeck({ title, author, theme, assets, footer, sectionTag, logos, steps });
//   const { pres, C, T, card, add, grp, anim, ... } = D;
//   ...逐页写...
//   D.write(process.argv[2], { loopMs: process.argv[3] === "checkin" ? 15000 : 0 });
//
// 规矩（为什么这么写，见 references/theme-mode.md）：
// - 版式只有 5 种：COVER 封面/封底，SECTION 章节，CONTENT 普通内容，HANDS 动手页（顶部进度条），STATEMENT 整页一句话。
// - 辅助信息（手册章节、限时）一律放右下角页码旁，小字。进度条小、半透明，只写出当前这一步。
// - 卡片和它上面的字用 grp() 包成一个组，讲者在 Keynote 里点一下就能整体加动画；anim() 直接写入入场动画。
"use strict";
const fs = require("fs");
const path = require("path");

function req(name) {
  const tries = [process.env.DEI_PPT_NODE_MODULES, path.join(__dirname, "node_modules"), undefined];
  for (const base of tries) {
    try { return base ? require(require.resolve(name, { paths: [base] })) : require(name); } catch (e) { /* 试下一个 */ }
  }
  throw new Error(`找不到 ${name}。在 skill 的 scripts 目录运行：npm install pptxgenjs@3.12.0`);
}
const pptxgen = req("pptxgenjs");
const JSZip = (() => { try { return require(require.resolve("jszip", { paths: [require.resolve("pptxgenjs", { paths: [process.env.DEI_PPT_NODE_MODULES || path.join(__dirname, "node_modules")] })] })); } catch (e) { return req("jszip"); } })();

const SLOTS = ["dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6", "hlink", "folHlink"];

// 默认主题：雾紫（取自 2026-11 一场沙龙的海报）。新项目用 poster_theme.py 从海报取色后覆盖 colors。
const DEFAULT_THEME = {
  name: "dei theme",
  head: "Source Han Sans SC Light",   // 标题、大字：细体显高级
  body: "Source Han Sans SC",         // 正文
  med: "Source Han Sans SC Medium",   // 指令框、强调大字
  en: "Bodoni 72 Smallcaps",          // 英文装饰字（封面底部 tagline、A/B/C 字母）
  colors: {
    dk1: "1E1B24", lt1: "FFFFFF", dk2: "57516A", lt2: "F7F6FC",
    accent1: "6E5FC0", // 主强调：标题高亮、数字、进度
    accent2: "8E9BE6",
    accent3: "ECE9FA", // 浅底：提示卡、chip
    accent4: "E5484D", // 警示红：只用于风险、编造
    accent5: "B9AEE8", // 线、未完成的点
    accent6: "D9DDF7", // 卡片描边
    hlink: "6E5FC0", folHlink: "8E9BE6",
  },
};

function createDeck(cfg = {}) {
  const theme = Object.assign({}, DEFAULT_THEME, cfg.theme || {});
  theme.colors = Object.assign({}, DEFAULT_THEME.colors, (cfg.theme || {}).colors || {});
  const A = (cfg.assets || ".").replace(/\/?$/, "/");
  const asset = (f) => (path.isAbsolute(f) ? f : A + f);
  const has = (f) => fs.existsSync(asset(f));
  const EN = theme.en, MED = theme.med;

  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
  pres.title = cfg.title || "";
  pres.author = cfg.author || "";
  pres.theme = { headFontFace: theme.head, bodyFontFace: theme.body };
  const C = pres.SchemeColor;

  // ---------- 版式 ----------
  const bg = (k) => (has(`bg_${k}.jpg`) ? { path: asset(`bg_${k}.jpg`) } : { color: k === "content" ? theme.colors.lt2 : theme.colors.lt2 });
  const footerObj = cfg.footer ? [{ text: { text: cfg.footer, options: { x: 0.8, y: 6.95, w: 5, h: 0.3, fontSize: 11, color: C.text2, margin: 0 } } }] : [];
  const slideNumber = { x: 12.0, y: 6.95, w: 0.6, h: 0.3, fontSize: 11, color: C.text2, align: "right" };
  const logos = (cfg.logos || []).filter((l) => has(l.file));
  // 章节页右下角一排 logo：按给定高度、从右往左排
  const sectionLogos = [];
  { let x = 12.35; for (const l of [...logos].reverse()) { const h = l.sectionH || 0.45, w = h * l.ratio; x -= w; sectionLogos.unshift({ image: { path: asset(l.file), x, y: 6.88 - h / 2, w, h } }); x -= 0.22; } }
  pres.defineSlideMaster({ title: "COVER", background: bg("cover"), objects: [] });
  pres.defineSlideMaster({
    title: "SECTION", background: bg("section"),
    objects: [
      ...(cfg.sectionTag ? [{ text: { text: cfg.sectionTag, options: { x: 0.9, y: 6.7, w: 6, h: 0.35, fontFace: EN, fontSize: 14, color: C.text2, charSpacing: 3, margin: 0 } } }] : []),
      ...sectionLogos,
      { placeholder: { options: { name: "title", type: "title", x: 0.9, y: 2.2, w: 11.5, h: 1.5, fontSize: 54, color: C.text1, align: "left", valign: "bottom", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", x: 0.9, y: 4.0, w: 11.5, h: 0.6, fontSize: 26, color: C.text2, align: "left", valign: "top", margin: 0 }, text: "" } },
    ],
  });
  pres.defineSlideMaster({
    title: "CONTENT", background: bg("content"),
    objects: [...footerObj, { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 0.45, w: 11.7, h: 0.95, fontSize: 36, color: C.text1, align: "left", valign: "middle", margin: 0 }, text: "" } }],
    slideNumber,
  });
  pres.defineSlideMaster({
    title: "HANDS", background: bg("content"),
    objects: [...footerObj, { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 1.15, w: 11.7, h: 0.95, fontSize: 36, fontFace: MED, color: C.text1, align: "left", valign: "middle", margin: 0 }, text: "" } }],
    slideNumber,
  });
  pres.defineSlideMaster({
    title: "STATEMENT", background: bg("content"),
    objects: [...footerObj, { placeholder: { options: { name: "body", type: "body", x: 1.2, y: 2.2, w: 10.9, h: 2.6, fontFace: theme.head, fontSize: 48, color: C.text1, align: "center", valign: "middle", margin: 0 }, text: "" } }],
    slideNumber,
  });

  // ---------- 分组与动画登记 ----------
  let n = 0, slideCount = 0, curGroup = null;
  const ANIMS = {}; // 幻灯片序号 → 动画步骤
  const oid = (s) => `${s}-${++n}`;
  const nm = (name) => (curGroup ? `grp:${curGroup}|${name}` : name);
  // grp(slide, "卡片1", () => { card(...); T(...); })：期间创建的元素打成一个组
  function grp(slide, name, fn) { const prev = curGroup; curGroup = name; try { fn(); } finally { curGroup = prev; } return name; }
  // anim(slide, [ "卡片1", "卡片2" ])：每项一次点击出现；也可写 { t: "卡片2", on: "after"|"with"|"click", fx: "fade"|"rise"|"wipe"|"appear", dur: 500 }
  function anim(slide, steps, defaults = {}) {
    ANIMS[slide._deiIdx] = (ANIMS[slide._deiIdx] || []).concat(steps.map((s) => Object.assign({ on: "click", fx: "fade", dur: 500 }, defaults, typeof s === "string" ? { t: s } : s)));
  }

  // ---------- 小部件 ----------
  function T(slide, text, o) { slide.addText(text, Object.assign({ isTextBox: true, margin: 0, color: C.text1, fontSize: 18 }, o, { objectName: nm((o && o.objectName) || oid("t")) })); }
  function card(slide, x, y, w, h, o = {}) {
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, Object.assign({
      x, y, w, h, rectRadius: 0.12, fill: { color: C.background1, transparency: 10 },
      line: { color: C.accent6, width: 1 },
      shadow: { type: "outer", color: theme.colors.accent1, opacity: 0.12, blur: 12, offset: 3, angle: 90 },
    }, o, { objectName: nm(o.objectName || oid("card")) }));
  }
  function chip(slide, x, y, text, o = {}) {
    const w = o.w || (0.36 + text.length * 0.2);
    slide.addText(text, { isTextBox: true, x, y, w, h: 0.42, fontSize: 14, color: o.color || C.accent1, align: "center", valign: "middle", margin: 0,
      shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.21, fill: { color: o.fill || C.accent3 }, line: { color: o.fill || C.accent5, width: 0.75 }, bold: !!o.bold, objectName: nm(oid("chip")) });
    return x + w + 0.15;
  }
  // 截图占位框：还没截到的真截图先放这个，交付时列进课前准备清单
  function ph(slide, x, y, w, h, label, o = {}) {
    slide.addText("📷  这里放：" + label, { isTextBox: true, x, y, w, h, fontSize: 14, color: o.red ? C.accent4 : C.accent1, align: "center", valign: "middle", margin: 0.15,
      shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.12, fill: { color: o.red ? "FDECEC" : C.accent3 },
      line: { color: o.red ? C.accent4 : C.accent1, width: 1.25, dashType: "dash" }, objectName: nm(oid("placeholder")) });
  }
  // 动手页顶部进度条：小、半透明，只写出当前这一步
  let STEPS = cfg.steps || [];
  function progress(slide, step, score) {
    const xs = STEPS.map((_, i) => 0.9 + i * 1.6), y = 0.5;
    if (xs.length > 1) slide.addShape(pres.shapes.LINE, { x: xs[0], y, w: xs[xs.length - 1] - xs[0], h: 0, line: { color: C.accent5, width: 1, transparency: 50 }, objectName: oid("progress-line") });
    xs.forEach((x, i) => {
      const cur = i + 1 === step, done = i + 1 < step, d = cur ? 0.17 : 0.11;
      slide.addShape(pres.shapes.OVAL, { x: x - d / 2, y: y - d / 2, w: d, h: d, objectName: oid("progress-dot"),
        fill: { color: cur || done ? C.accent1 : C.background1, transparency: cur ? 0 : 50 }, line: { color: C.accent1, width: 1, transparency: cur ? 0 : 50 } });
    });
    T(slide, `${cfg.stepWord || "第 %d 轮"}`.replace("%d", step) + ` · ${STEPS[step - 1]}`, { x: xs[xs.length - 1] + 0.3, y: y - 0.16, w: 4, h: 0.32, fontSize: 12, color: C.accent1, valign: "middle" });
    if (score) {
      slide.addText([{ text: score + "  ", options: { color: C.text2 } }, { text: "____ / 10", options: { bold: true, color: C.accent1 } }],
        { isTextBox: true, x: 10.75, y: 0.3, w: 1.8, h: 0.42, fontSize: 13, align: "center", valign: "middle", margin: 0,
          shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.21, fill: { color: C.background1 }, line: { color: C.accent5, width: 1 }, objectName: oid("score") });
    }
  }
  // 手册章节和限时：右下角页码旁一行小字（手册提前发过，不每页放二维码）
  function foot(slide, manual, mins) {
    const r = [];
    if (manual) r.push({ text: (cfg.manualWord || "手册 ") + manual, options: { color: C.text2 } });
    if (mins) { if (r.length) r.push({ text: "   ·   ", options: { color: C.text2 } }); r.push({ text: "限时 " + mins, options: { color: C.accent1 } }); }
    if (r.length) T(slide, r, { x: 7.4, y: 6.95, w: 4.4, h: 0.3, fontSize: 12, align: "right", valign: "middle" });
  }
  function pathRow(slide, y, tag, text, o = {}) {
    chip(slide, 0.8, y + 0.04, tag, { w: 0.9, fill: o.fill, color: o.color, bold: true });
    T(slide, text, { x: 1.9, y, w: o.w || 9.2, h: 0.5, fontSize: o.size || 24, valign: "middle" });
  }
  function bullets(items, o = {}) {
    return items.map((t, i) => ({ text: t, options: Object.assign({ bullet: { indent: 20 }, paraSpaceAfter: o.space || 8, breakLine: i < items.length - 1 }, o.run || {}) }));
  }
  function numbered(slide, x, y, w, items, o = {}) {
    const gap = o.gap || 0.62, names = [];
    items.forEach((t, i) => {
      const g = o.group ? `${o.group}${i + 1}` : null;
      const draw = () => {
        slide.addText(String(i + 1), { isTextBox: true, x, y: y + i * gap, w: 0.42, h: 0.42, shape: pres.shapes.OVAL, fill: { color: C.accent1 }, color: C.background1, fontSize: 16, bold: true, align: "center", valign: "middle", margin: 0, objectName: nm(oid("num")) });
        T(slide, t, { x: x + 0.6, y: y + i * gap - 0.04, w: w - 0.6, h: 0.5, fontSize: o.size || 20, valign: "middle" });
      };
      if (g) { grp(slide, g, draw); names.push(g); } else draw();
    });
    return names;
  }
  // 标题里只标一处关键短语
  const TT = (a, hi, b = "") => [{ text: a }, { text: hi, options: { color: C.accent1 } }, { text: b }];

  const SECS = new Set();
  function add(master, section, opts = {}) {
    if (!SECS.has(section)) { pres.addSection({ title: section }); SECS.add(section); }
    const s = pres.addSlide({ masterName: master, sectionTitle: section });
    s._deiIdx = ++slideCount;
    if (opts.hidden) s.hidden = true;
    if (opts.note) s.addNotes(opts.note);
    return s;
  }

  // ---------- 常用页面模板 ----------
  const P = {};
  // 封面 / 封底：和海报一个样子。logos 排左上；tags 是底部三段英文装饰字
  P.cover = (sec, o) => {
    const s = add("COVER", sec);
    let x = 0.8;
    logos.forEach((l) => { const h = l.coverH || 0.55, w = h * l.ratio; s.addImage({ path: asset(l.file), x, y: 0.87 - h / 2, w, h, objectName: "logo-" + l.name }); x += w + 0.35; });
    if (o.year) T(s, o.year, { x: 10.6, y: 0.55, w: 1.95, h: 0.6, fontFace: EN, fontSize: 32, align: "right" });
    T(s, o.title, { x: 0.8, y: 2.05, w: 11.73, h: 1.5, fontFace: o.titleFont || "Source Han Sans SC ExtraLight", fontSize: o.titleSize || 76, align: "center", valign: "middle", objectName: "封面标题" });
    if (o.subtitle) T(s, o.subtitle, { x: 0.8, y: 3.6, w: 11.73, h: 0.7, fontFace: theme.head, fontSize: 32, align: "center" });
    if (o.info) T(s, o.info, { x: 0.8, y: 4.75, w: 11.73, h: 0.45, fontSize: 18, align: "center", color: C.text2 });
    (o.tags || []).forEach((t, i, a) => T(s, t, { x: [0.8, 4.67, 8.53][i], y: 6.75, w: 4, h: 0.35, fontFace: EN, fontSize: 14, color: C.text2, charSpacing: 2, align: ["left", "center", "right"][i] }));
    s.addNotes(o.note || "封面。");
    return s;
  };
  P.closing = (sec, o) => {
    const s = add("COVER", sec);
    const ws = logos.map((l) => (l.closeH || 0.62) * l.ratio), tot = ws.reduce((a, b) => a + b, 0) + 0.5 * Math.max(0, ws.length - 1);
    let x = (13.333 - tot) / 2;
    logos.forEach((l, i) => { const h = l.closeH || 0.62; s.addImage({ path: asset(l.file), x, y: 1.6 - h / 2, w: ws[i], h, objectName: "logo-" + l.name }); x += ws[i] + 0.5; });
    T(s, o.title, { x: 0.8, y: 2.6, w: 11.73, h: 1.3, fontFace: o.titleFont || "Source Han Sans SC ExtraLight", fontSize: 66, align: "center", valign: "middle", objectName: "结尾标题" });
    if (o.subtitle) T(s, o.subtitle, { x: 0.8, y: 4.0, w: 11.73, h: 0.7, fontSize: 28, align: "center", fontFace: theme.head });
    (o.tags || []).forEach((t, i) => T(s, t, { x: [0.8, 4.67, 8.53][i], y: 6.75, w: 4, h: 0.35, fontFace: EN, fontSize: 14, color: C.text2, charSpacing: 2, align: ["left", "center", "right"][i] }));
    s.addNotes(o.note || "封底。");
    return s;
  };
  P.section = (sec, title, sub, note) => { const s = add("SECTION", sec); s.addText(title, { placeholder: "title" }); if (sub) s.addText(sub, { placeholder: "body" }); if (note) s.addNotes(note); return s; };
  // 人物页：照片左、信息一栏排；同一字号同一颜色，只把成果里的数字标强调色。rows 里 null = 分组间隔
  P.person = (sec, o) => {
    const s = add("CONTENT", sec);
    if (o.photo && has(o.photo)) s.addImage({ path: asset(o.photo), x: 0.59, y: 1.04, w: 3.92, h: 5.23, sizing: { type: "cover", w: 3.92, h: 5.23 }, objectName: "人像照" });
    else ph(s, 0.8, 0.7, 3.5, 5.9, "人像照（竖版）");
    T(s, o.name, { x: 4.9, y: 0.75, w: 6, h: 0.9, fontFace: theme.head, fontSize: 44 });
    if (o.tagline) T(s, o.tagline, { x: 4.9, y: 1.65, w: 7.6, h: 0.45, fontSize: 18, color: C.text2 });
    s.addShape(pres.shapes.LINE, { x: 4.9, y: 2.4, w: 7.6, h: 0, line: { color: C.accent5, width: 0.75 }, objectName: oid("分隔线") });
    let ry = 2.65, gi = 0; const groups = [[]];
    o.rows.forEach((r) => {
      if (!r) { ry += 0.22; groups.push([]); gi++; return; }
      const g = `行${gi + 1}-${groups[gi].length + 1}`; groups[gi].push(g);
      grp(s, g, () => {
        s.addShape(pres.shapes.OVAL, { x: 4.92, y: ry + 0.2, w: 0.09, h: 0.09, fill: { color: C.accent1 }, line: { color: C.accent1, width: 0.5 }, objectName: nm(oid("dot")) });
        T(s, r.map(([t, hi]) => ({ text: t, options: hi ? { color: C.accent1, bold: true } : {} })), { x: 5.2, y: ry, w: 7.3, h: 0.5, fontSize: 18, valign: "middle" });
      });
      ry += 0.52;
    });
    // 动画：每组第一行点击出现，组内其余接着上一条依次出来
    if (o.animate !== false) anim(s, groups.flatMap((g) => g.map((name, i) => ({ t: name, on: i ? "after" : "click", fx: "rise", dur: 400 }))));
    s.addNotes(o.note || "自我介绍。");
    return s;
  };
  // 时间轴（今天的流程）；hi = 高亮第几个（从 0 起）
  P.agenda = (sec, o) => {
    const s = add("CONTENT", sec);
    s.addText(o.title || "今天的流程", { placeholder: "title" });
    const k = o.items.length, x0 = 1.3, gap = (10.6) / Math.max(1, k - 1), y = 3.3;
    s.addShape(pres.shapes.LINE, { x: x0, y, w: gap * (k - 1), h: 0, line: { color: C.accent5, width: 1.5 }, objectName: "时间轴" });
    o.items.forEach(([t, name], i) => {
      const me = i === o.hi, d = me ? 0.36 : 0.22, x = x0 + i * gap;
      s.addShape(pres.shapes.OVAL, { x: x - d / 2, y: y - d / 2, w: d, h: d, fill: { color: me ? C.accent1 : C.background1 }, line: { color: C.accent1, width: 1.5 }, objectName: oid("node") });
      T(s, t, { x: x - 1.2, y: y - 1.05, w: 2.4, h: 0.55, fontSize: 26, align: "center", fontFace: theme.head, color: me ? C.accent1 : C.text1 });
      T(s, name, { x: x - 1.2, y: y + 0.4, w: 2.4, h: 0.45, fontSize: 18, align: "center", bold: me, color: me ? C.accent1 : C.text1 });
    });
    if (o.callout) { card(s, 6.05, 4.75, 5.3, 1.05, { fill: { color: C.accent3 }, line: { color: C.accent5, width: 1 } }); T(s, o.callout, { x: 6.3, y: 4.75, w: 4.9, h: 1.05, fontSize: 18, valign: "middle" }); }
    s.addNotes(o.note || "今天的流程。");
    return s;
  };
  // 整页一句话
  P.statement = (sec, o) => {
    const s = add("STATEMENT", sec);
    if (o.kicker) T(s, o.kicker, { x: 0.8, y: 1.4, w: 11.73, h: 0.6, fontSize: 26, color: C.text2, align: "center" });
    s.addText(o.text, { placeholder: "body", fontSize: o.size || 48 });
    if (o.sub) T(s, o.sub, { x: 0.8, y: 4.95, w: 11.73, h: 0.5, fontSize: 22, color: C.text2, align: "center" });
    if (o.chip) chip(s, (13.333 - 4.0) / 2, 5.75, o.chip, { w: 4.0, fill: C.accent1, color: C.background1, bold: true });
    s.addNotes(o.note || "");
    return s;
  };
  // 引文页：引文 + 出处 + 一句「所以呢」
  P.quote = (sec, o) => {
    const s = add("STATEMENT", sec);
    T(s, "“", { x: 1.2, y: 0.9, w: 1.5, h: 1.4, fontFace: EN, fontSize: 110, color: C.accent5 });
    s.addText(o.text, { placeholder: "body", fontSize: 44 });
    T(s, o.src, { x: 1.2, y: 4.85, w: 10.9, h: 0.4, fontSize: 16, color: C.text2, align: "center" });
    if (o.line) T(s, o.line, { x: 1.2, y: 5.5, w: 10.9, h: 0.9, fontSize: 22, color: C.accent1, align: "center" });
    s.addNotes(o.note || "");
    return s;
  };
  // 一行 N 张概览卡（如「成本就五样」）：大字 + 类别 + 例子；默认点一下依次出来
  P.cardRow = (sec, o) => {
    const s = add("CONTENT", sec);
    s.addText(o.title, { placeholder: "title" });
    const k = o.items.length, gapX = 0.2, w = (11.7 - gapX * (k - 1)) / k, names = [];
    o.items.forEach(([big, kind, list], i) => {
      const x = 0.8 + i * (w + gapX), g = `卡${i + 1}`; names.push(g);
      grp(s, g, () => {
        card(s, x, 1.75, w, 3.0);
        T(s, big, { x: x + 0.25, y: 2.0, w: w - 0.4, h: 0.75, fontSize: 32, fontFace: theme.head, color: C.accent1 });
        T(s, kind, { x: x + 0.25, y: 2.8, w: w - 0.4, h: 0.45, fontSize: 18, bold: true });
        if (list) T(s, list, { x: x + 0.25, y: 3.4, w: w - 0.35, h: 1.2, fontSize: 15, color: C.text2, valign: "top", paraSpaceAfter: 4 });
      });
    });
    if (o.line) T(s, o.line, { x: 0.8, y: 5.25, w: 11.7, h: 0.5, fontSize: 20, align: "center" });
    if (o.animate !== false) anim(s, names.map((t, i) => ({ t, on: i ? "after" : "click", fx: "rise", dur: 350 })));
    s.addNotes(o.note || "");
    return s;
  };
  // 三张对比卡（工具 / 方案）：名字 + 适合 + 好在 + 要注意；默认每张点一下出来（讲一张出一张）
  P.compare3 = (sec, o) => {
    const s = add("CONTENT", sec);
    s.addText(o.title, { placeholder: "title" });
    const names = [];
    o.items.forEach(([name, fit, pro, con], i) => {
      const x = 0.8 + i * 3.97, y = 1.65, g = `卡${i + 1}`; names.push(g);
      grp(s, g, () => {
        card(s, x, y, 3.77, 4.3);
        T(s, name, { x: x + 0.3, y: y + 0.3, w: 3.2, h: 0.65, fontSize: 26, fontFace: theme.head, valign: "middle", fit: "shrink" });
        T(s, fit, { x: x + 0.3, y: y + 1.0, w: 3.2, h: 0.7, fontSize: 15, color: C.accent1, valign: "top" });
        s.addShape(pres.shapes.LINE, { x: x + 0.3, y: y + 1.85, w: 3.17, h: 0, line: { color: C.accent6, width: 0.75 }, objectName: nm(oid("分隔线")) });
        [[o.labels ? o.labels[0] : "好在", pro], [o.labels ? o.labels[1] : "要注意", con]].forEach(([lab, t], k) => {
          T(s, lab, { x: x + 0.3, y: y + 2.05 + k * 1.1, w: 3.2, h: 0.3, fontSize: 13, color: C.text2 });
          T(s, t, { x: x + 0.3, y: y + 2.38 + k * 1.1, w: 3.2, h: 0.7, fontSize: 17, valign: "top" });
        });
      });
    });
    if (o.punch) T(s, o.punch, { x: 0.8, y: 6.2, w: 11.7, h: 0.45, fontSize: 18, color: C.accent1, align: "center" });
    if (o.animate !== false) anim(s, names.map((t) => ({ t, fx: "fade" })));
    s.addNotes(o.note || "");
    return s;
  };
  // 指令页：一个大指令框（学员照着发的那句话）+ 一行提醒；点一下指令框出现
  P.instruction = (sec, o) => {
    const s = add(o.master || "HANDS", sec);
    if (o.step) progress(s, o.step, o.score);
    s.addText(o.title, { placeholder: "title" });
    grp(s, "指令框", () => {
      card(s, 0.8, 2.75, 11.7, 1.9, o.accentBox ? { fill: { color: C.accent3 }, line: { color: C.accent3, width: 1 } } : {});
      T(s, o.prompt, { x: 1.2, y: 2.75, w: 10.9, h: 1.9, fontSize: o.size || 30, valign: "middle", fontFace: o.bold ? MED : undefined, color: o.accentBox ? C.accent1 : C.text1 });
    });
    if (o.hint) T(s, o.hint, { x: 0.8, y: 5.0, w: 11.7, h: 0.45, fontSize: 18, color: C.text2 });
    foot(s, o.manual, o.mins);
    if (o.animate) anim(s, ["指令框"]);
    s.addNotes(o.note || "");
    return s;
  };
  // 以前 → 现在
  P.beforeAfter = (s, o) => {
    grp(s, "以前", () => {
      card(s, 0.8, 2.6, 5.7, 2.0);
      T(s, o.beforeLabel || "以前", { x: 1.15, y: 2.85, w: 5, h: 0.4, fontSize: 16, color: C.text2 });
      T(s, [{ text: o.before[0], options: { breakLine: true } }, { text: o.before[1], options: { color: C.accent4, fontSize: 18 } }], { x: 1.15, y: 3.3, w: 5.1, h: 1.1, fontSize: 24, valign: "top", paraSpaceAfter: 8 });
    });
    grp(s, "现在", () => {
      T(s, "→", { x: 6.5, y: 2.6, w: 0.8, h: 2.0, fontSize: 40, color: C.accent1, align: "center", valign: "middle" });
      card(s, 7.3, 2.6, 5.2, 2.0, { fill: { color: C.accent1 }, line: { color: C.accent1, width: 1 } });
      T(s, o.afterLabel || "现在", { x: 7.65, y: 2.85, w: 4.6, h: 0.4, fontSize: 16, color: C.background1 });
      T(s, [{ text: o.after[0], options: { breakLine: true } }, { text: o.after[1], options: { fontSize: 18 } }], { x: 7.65, y: 3.3, w: 4.6, h: 1.1, fontSize: 24, valign: "top", color: C.background1, paraSpaceAfter: 8 });
    });
    anim(s, [{ t: "现在", fx: "wipe" }]);
  };
  // 案例卡：居中排，三张视觉重量一致
  P.cases = (sec, o) => {
    const s = add("CONTENT", sec);
    s.addText(o.title, { placeholder: "title" });
    const names = [];
    o.items.forEach(([big, who, t], i) => {
      const x = 0.8 + i * 3.97, g = `案例${i + 1}`; names.push(g);
      grp(s, g, () => {
        card(s, x, 1.75, 3.77, 3.55);
        T(s, big, { x: x + 0.25, y: 2.05, w: 3.27, h: 0.9, fontSize: 38, color: C.accent1, fontFace: theme.head, align: "center", valign: "middle" });
        s.addShape(pres.shapes.LINE, { x: x + 1.48, y: 3.1, w: 0.8, h: 0, line: { color: C.accent5, width: 1 }, objectName: nm(oid("分隔线")) });
        T(s, who, { x: x + 0.25, y: 3.25, w: 3.27, h: 0.45, fontSize: 18, bold: true, align: "center" });
        T(s, t, { x: x + 0.3, y: 3.8, w: 3.17, h: 1.4, fontSize: 16, color: C.text2, align: "center", valign: "top" });
      });
    });
    if (o.foot) T(s, o.foot, { x: 0.8, y: 5.7, w: 11.7, h: 0.45, fontSize: 15, color: C.text2, align: "center" });
    if (o.animate !== false) anim(s, names.map((t) => ({ t, fx: "fade" })));
    s.addNotes(o.note || "");
    return s;
  };
  // 打勾清单（「你现在拥有了什么」）：一条接一条出来
  P.checklist = (s, items, o = {}) => {
    const names = [];
    items.forEach((t, i) => {
      const y = (o.y || 1.75) + i * (o.gap || 0.82), g = `勾${i + 1}`; names.push(g);
      grp(s, g, () => {
        s.addText("✓", { isTextBox: true, x: 0.8, y: y + 0.06, w: 0.45, h: 0.45, shape: pres.shapes.OVAL, fill: { color: C.accent1 }, color: C.background1, fontSize: 16, bold: true, align: "center", valign: "middle", margin: 0, objectName: nm(oid("check")) });
        T(s, t, { x: 1.45, y, w: o.w || 6.2, h: 0.58, fontSize: 19, valign: "middle" });
      });
    });
    anim(s, names.map((t, i) => ({ t, on: i ? "after" : "click", fx: "rise", dur: 350 })));
    return names;
  };

  // ---------- 写出与后处理 ----------
  async function write(out, opt = {}) {
    await pres.writeFile({ fileName: out });
    const zip = await JSZip.loadAsync(fs.readFileSync(out));
    // 1. 主题色写进 theme1.xml（pptxgenjs 只写字体）
    const tp = "ppt/theme/theme1.xml";
    let tx = await zip.file(tp).async("string");
    for (const k of SLOTS) if (!/^[0-9A-Fa-f]{6}$/.test(theme.colors[k])) throw new Error(`theme.colors.${k} 必须是 6 位十六进制`);
    const tname = String(theme.name).replace(/[&<>"]/g, "");
    tx = tx.replace(/<a:clrScheme\b[\s\S]*?<\/a:clrScheme>/, `<a:clrScheme name="${tname}">` + SLOTS.map((k) => `<a:${k}><a:srgbClr val="${theme.colors[k].toUpperCase()}"/></a:${k}>`).join("") + "</a:clrScheme>")
      .replace(/(<a:(?:theme|fontScheme)\b[^>]*?\bname=")[^"]*"/g, (_, h) => `${h}${tname}"`)
      .replace(/(<a:majorFont>[\s\S]*?)<a:ea typeface="[^"]*"\s*\/>/, `$1<a:ea typeface="${theme.head}"/>`)
      .replace(/(<a:minorFont>[\s\S]*?)<a:ea typeface="[^"]*"\s*\/>/, `$1<a:ea typeface="${theme.body}"/>`);
    zip.file(tp, tx);
    for (const name of Object.keys(zip.files)) {
      if (!/^ppt\/(slides|slideLayouts|slideMasters)\/[^/]+\.xml$/.test(name)) continue;
      let x = await zip.file(name).async("string");
      // 2. 中文要单独指定东亚字体（a:ea），否则 Keynote / PowerPoint 退回系统默认字体
      x = x.replace(/<a:latin typeface="([^"]+)"([^>]*)\/>(?!<a:ea)/g, (m, f, rest) => `<a:latin typeface="${f}"${rest}/><a:ea typeface="${f}"/><a:cs typeface="${f}"/>`);
      const sm = name.match(/^ppt\/slides\/slide(\d+)\.xml$/);
      if (sm) {
        x = groupShapes(x);
        const steps = ANIMS[+sm[1]];
        if (steps && steps.length) x = addTiming(x, steps, name);
        // 3. 签到轮播：每页定时自动翻
        if (opt.loopMs && !x.includes("<p:transition")) x = x.replace("</p:clrMapOvr>", `</p:clrMapOvr><p:transition spd="slow" advTm="${opt.loopMs}"><p:fade/></p:transition>`);
      }
      zip.file(name, x);
    }
    if (opt.loopMs) {
      let pp = await zip.file("ppt/presProps.xml").async("string");
      pp = pp.replace(/<p:presentationPr([^>]*)\/>/, `<p:presentationPr$1><p:showPr loop="1" showNarration="1"><p:present/><p:sldAll/><p:penClr><a:prstClr val="red"/></p:penClr></p:showPr></p:presentationPr>`);
      zip.file("ppt/presProps.xml", pp);
    }
    // 4. 去掉 ZIP 里的文件夹条目（云盘协同打开时会失败）
    const clean = new JSZip();
    for (const [k, f] of Object.entries(zip.files)) if (!f.dir) clean.file(k, await f.async("nodebuffer"), { createFolders: false });
    fs.writeFileSync(out, await clean.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
    console.log("wrote", out, `(${slideCount} 页)`);
  }

  return { pres, C, theme, A, asset, EN, MED, T, card, chip, ph, progress, foot, pathRow, bullets, numbered, TT, add, grp, anim, oid, nm, P,
    setSteps: (s) => { STEPS = s; }, write };
}

// ---------- 后处理：把 grp:名字| 前缀的元素包成 <p:grpSp> ----------
function groupShapes(x) {
  if (!x.includes('name="grp:')) return x;
  const re = /<p:(sp|pic|cxnSp)>[\s\S]*?<\/p:\1>/g;
  const els = []; let m;
  while ((m = re.exec(x))) {
    const nmm = m[0].match(/<p:cNvPr id="(\d+)" name="grp:([^|"]+)\|([^"]*)"/);
    if (nmm) els.push({ start: m.index, end: m.index + m[0].length, xml: m[0], g: nmm[2] });
  }
  if (!els.length) return x;
  let maxId = Math.max(...[...x.matchAll(/<p:cNvPr id="(\d+)"/g)].map((k) => +k[1]));
  const groups = {};
  for (const e of els) (groups[e.g] = groups[e.g] || []).push(e);
  // 从后往前替换，保持偏移有效；每组放在它第一个成员的位置
  const edits = [];
  for (const [g, members] of Object.entries(groups)) {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const e of members) {
      const off = e.xml.match(/<a:off x="(-?\d+)" y="(-?\d+)"\/>/), ext = e.xml.match(/<a:ext cx="(\d+)" cy="(\d+)"\/>/);
      if (!off || !ext) continue;
      x0 = Math.min(x0, +off[1]); y0 = Math.min(y0, +off[2]); x1 = Math.max(x1, +off[1] + +ext[1]); y1 = Math.max(y1, +off[2] + +ext[2]);
    }
    const inner = members.map((e) => e.xml.replace(/name="grp:[^|"]+\|/, 'name="')).join("");
    const gx = `<p:grpSp><p:nvGrpSpPr><p:cNvPr id="${++maxId}" name="${g}"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="${x0}" y="${y0}"/><a:ext cx="${x1 - x0}" cy="${y1 - y0}"/><a:chOff x="${x0}" y="${y0}"/><a:chExt cx="${x1 - x0}" cy="${y1 - y0}"/></a:xfrm></p:grpSpPr>${inner}</p:grpSp>`;
    members.forEach((e, i) => edits.push({ start: e.start, end: e.end, txt: i === 0 ? gx : "" }));
  }
  edits.sort((a, b) => b.start - a.start);
  for (const e of edits) x = x.slice(0, e.start) + e.txt + x.slice(e.end);
  return x;
}

// ---------- 后处理：入场动画（PowerPoint 时间轴，Keynote 也能读） ----------
const FX = {
  appear: { id: 1, sub: 0 }, fade: { id: 10, sub: 0 }, wipe: { id: 22, sub: 8 }, rise: { id: 42, sub: 0 },
};
function addTiming(x, steps, name) {
  const ids = {};
  for (const m of x.matchAll(/<p:cNvPr id="(\d+)" name="([^"]*)"/g)) if (!(m[2] in ids)) ids[m[2]] = m[1];
  let id = 2; const nid = () => ++id;
  const tgt = (sp) => `<p:tgtEl><p:spTgt spid="${sp}"/></p:tgtEl>`;
  const effect = (st, sp, nodeType) => {
    const f = FX[st.fx] || FX.fade, d = st.dur;
    let body = `<p:set><p:cBhvr><p:cTn id="${nid()}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>${tgt(sp)}<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set>`;
    if (st.fx === "fade" || st.fx === "rise") body += `<p:animEffect transition="in" filter="fade"><p:cBhvr><p:cTn id="${nid()}" dur="${d}"/>${tgt(sp)}</p:cBhvr></p:animEffect>`;
    if (st.fx === "wipe") body += `<p:animEffect transition="in" filter="wipe(left)"><p:cBhvr><p:cTn id="${nid()}" dur="${d}"/>${tgt(sp)}</p:cBhvr></p:animEffect>`;
    if (st.fx === "rise") {
      const a = (attr, from, to) => `<p:anim calcmode="lin" valueType="num"><p:cBhvr><p:cTn id="${nid()}" dur="${d}" decel="100000" fill="hold"/>${tgt(sp)}<p:attrNameLst><p:attrName>${attr}</p:attrName></p:attrNameLst></p:cBhvr><p:tavLst><p:tav tm="0"><p:val><p:strVal val="${from}"/></p:val></p:tav><p:tav tm="100000"><p:val><p:strVal val="${to}"/></p:val></p:tav></p:tavLst></p:anim>`;
      body += a("ppt_x", "#ppt_x", "#ppt_x") + a("ppt_y", "#ppt_y+.1", "#ppt_y");
    }
    return `<p:par><p:cTn id="${nid()}" presetID="${f.id}" presetClass="entr" presetSubtype="${f.sub}" fill="hold" nodeType="${nodeType}"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>${body}</p:childTnLst></p:cTn></p:par>`;
  };
  // 按点击分段：click 开新的一段；with 与上一条同时；after 接在上一条后面
  const clicks = [];
  for (const st of steps) {
    const sp = ids[st.t];
    if (!sp) { console.warn(`⚠️ ${name}: 动画目标「${st.t}」不存在，已跳过`); continue; }
    if (st.on === "click" || !clicks.length) clicks.push([{ st, sp, at: 0, node: "clickEffect" }]);
    else { const c = clicks[clicks.length - 1], last = c[c.length - 1]; c.push({ st, sp, at: st.on === "with" ? last.at : last.at + last.st.dur, node: st.on === "with" ? "withEffect" : "afterEffect" }); }
  }
  if (!clicks.length) return x;
  const parts = clicks.map((c) => {
    const byT = {}; c.forEach((e) => (byT[e.at] = byT[e.at] || []).push(e));
    const inner = Object.keys(byT).map(Number).sort((a, b) => a - b).map((t) => `<p:par><p:cTn id="${nid()}" fill="hold"><p:stCondLst><p:cond delay="${t}"/></p:stCondLst><p:childTnLst>${byT[t].map((e) => effect(e.st, e.sp, e.node)).join("")}</p:childTnLst></p:cTn></p:par>`).join("");
    return `<p:par><p:cTn id="${nid()}" fill="hold"><p:stCondLst><p:cond delay="indefinite"/></p:stCondLst><p:childTnLst>${inner}</p:childTnLst></p:cTn></p:par>`;
  }).join("");
  const timing = `<p:timing><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst><p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>${parts}</p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst><p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq></p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>`;
  if (x.includes("</p:transition>")) return x.replace("</p:transition>", "</p:transition>" + timing);
  if (/<p:transition[^>]*\/>/.test(x)) return x.replace(/(<p:transition[^>]*\/>)/, "$1" + timing);
  return x.replace("</p:clrMapOvr>", "</p:clrMapOvr>" + timing);
}

module.exports = { createDeck, DEFAULT_THEME, groupShapes, addTiming };
