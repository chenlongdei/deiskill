// 主题版内容文件模板：复制到 <课程文件夹>/_scripts/<项目>_deck.js，把【】里的内容换成真的。
// 构建：python3 <dei-ppt>/scripts/build.py <项目>_deck.js ../PPT --name "<文件名>" --checkin 签到轮播 --pdf
// 素材放在 ../PPT/assets/：bg_cover.jpg、bg_section.jpg、bg_content.jpg（poster_theme.py backgrounds 生成）、logo_*.png、photo.jpg
// 写法规矩见 references/theme-mode.md：一页只放一个重点，辅助信息放右下角，卡片和字打组，讲稿写成能直接念的话。
const path = require("path");
const E = require(process.env.DEI_PPT_ENGINE || path.join(__dirname, "deck_engine.js"));
const OUT = process.argv[2];
const CHECKIN = process.argv[3] === "checkin";

const D = E.createDeck({
  title: "【活动名】", author: "【讲者署名】",
  assets: process.env.DECK_ASSETS || path.join(__dirname, "..", "PPT", "assets"),
  theme: { name: "【主题名】" /* , colors: { ...poster_theme.py palette 的输出 } */ },
  footer: "【活动名 · 环节名】",
  sectionTag: "【英文 tagline，可留空】",
  logos: [ // ratio = 宽 ÷ 高；三个高度分别是封面、章节页、封底上的显示高度（英寸）
    { name: "主办方", file: "logo_host.png", ratio: 3.6, coverH: 0.57, sectionH: 0.48, closeH: 0.63 },
    { name: "讲者", file: "logo_me.png", ratio: 4.6, coverH: 0.48, sectionH: 0.4, closeH: 0.55 },
  ],
  steps: ["【第一步】", "【第二步】", "【第三步】"], // 动手页顶部进度条
});
const { C, T, card, ph, progress, foot, TT, add, grp, anim, P } = D;
const TAGS = ["【TAG】", "【TAG】", "【TAG】"];

// ===== 签到（正片前 4 页 = 签到轮播）=====
const S0 = CHECKIN ? "签到轮播" : "签到";
P.cover(S0, { title: "【活动名】", subtitle: "【副标题】", info: "【日期 时间 · 地点】", year: "【年份】", tags: TAGS, note: "签到时轮播。" });
{ // 连网和装软件：三张卡
  const s = add("CONTENT", S0);
  s.addText(TT("先连网，再把 ", "AI 装好"), { placeholder: "title" });
  card(s, 0.8, 1.7, 4.1, 4.3); T(s, "WiFi", { x: 1.15, y: 1.95, w: 3.4, h: 0.5, color: C.accent1, bold: true });
  T(s, "名称 __________\n密码 __________", { x: 1.15, y: 2.6, w: 3.5, h: 2, fontSize: 24, valign: "top" });
  card(s, 5.15, 1.7, 4.1, 4.3); T(s, "装好一个 AI", { x: 5.5, y: 1.95, w: 3.4, h: 0.5, color: C.accent1, bold: true });
  T(s, "【电脑用什么】\n【手机用什么】", { x: 5.5, y: 2.6, w: 3.5, h: 2, fontSize: 28, valign: "top" });
  card(s, 9.5, 1.7, 3.03, 4.3); ph(s, 9.8, 1.95, 2.43, 2.43, "群二维码");
  s.addNotes("签到轮播。WiFi 现场填。");
}
const person = (sec, note) => P.person(sec, {
  photo: "photo.jpg", name: "【署名】", tagline: "【一句话身份 · 城市】",
  rows: [[["【背书 1：机构、课程、平台】"]], [["【背书 2】"]], null, [["【成果：谁，做到了 "], ["【能直接核实的数字】", 1]]],
  animate: !CHECKIN, note: note || "自我介绍。",
});
person(S0);
P.agenda(S0, { items: [["14:00", "签到"], ["14:30", "开场"], ["15:00", "动手"], ["16:30", "交流"]], hi: 2, callout: "【这一段要带什么】" });

if (!CHECKIN) {
  // ===== 开场 =====
  const S1 = "开场";
  P.section(S1, "【环节名】", "【一句话：从什么到什么】", "【接上一位讲者的过渡话】");
  person(S1, "【自我介绍讲稿：熟悉我的朋友知道……】");
  P.cardRow(S1, { title: TT("【一句话概括，", "高亮词", "】"), line: "【这一组卡片的结论】",
    items: [["【大字】", "【类别】", "【例子】"], ["【大字】", "【类别】", "【例子】"], ["【大字】", "【类别】", "【例子】"]], note: "【讲稿】" });
  P.compare3(S1, { title: TT("【类别 · 】", "【名称】", "【：一句话】"), punch: "【这一类的提醒】",
    items: [["【工具 A】", "【适合干什么】", "【好在哪】", "【要注意：讲者踩过的坑】"], ["【工具 B】", "…", "…", "…"], ["【工具 C】", "…", "…", "…"]], note: "【讲稿】" });

  // ===== 动手一轮 =====
  const R1 = "第 1 轮";
  P.instruction(R1, { step: 1, title: TT("【回到哪里，】", "【做什么】"), prompt: "【学员照着发的那一句话】", hint: "注意：【最容易做错的一点】",
    manual: "2.1", mins: "2 分钟", animate: true, note: "【讲稿：念一遍指令，等待片刻】" });
  P.statement(R1, { kicker: "【一个问题】", text: "【这一轮揭示的一句话，\n分两行】", note: "【讲稿】" });
  P.quote(R1, { text: "【引文】", src: "—— 【作者《书名》章节】", line: "【所以呢：一句话接回今天】", note: "【讲稿；引文版本待核时写进清单】" });
  { const s = add("HANDS", R1); progress(s, 1); s.addText(TT("【以前怎样，】", "【现在怎样】"), { placeholder: "title" });
    P.beforeAfter(s, { before: ["【以前的做法】", "【问题】"], after: ["【现在的做法】", "【我现场演示】"] }); foot(s, "4.3", "2 分钟"); s.addNotes("【讲稿】"); }

  // ===== 收尾 =====
  const R9 = "收尾";
  { const s = add("CONTENT", R9); s.addText(TT("你现在", "拥有了什么"), { placeholder: "title" }); P.checklist(s, ["【带走的第 1 样】", "【第 2 样】", "【第 3 样】"]); s.addNotes("【讲稿】"); }
  P.cases(R9, { title: "我们做过的", foot: "【想看更多怎么联系】",
    items: [["【数字】", "【谁】", "【一句话：原来怎样，现在怎样】"], ["【数字】", "【谁】", "【…】"], ["【数字】", "【谁】", "【…】"]], note: "【讲稿；学员案例上屏前先问本人同意】" });
  P.closing(R9, { title: "【合影 · 自由交流】", subtitle: "【一句话】", tags: TAGS, note: "【封底挂着时做什么】" });

  // ===== 备用页（隐藏）=====
  const BK = "备用页（隐藏）";
  { const s = add("STATEMENT", BK, { hidden: true, note: "（【什么情况】跳到这页）【怎么说】" });
    T(s, "B1 · 【情况】", { x: 0.8, y: 1.4, w: 11.73, h: 0.6, fontSize: 26, color: C.text2, align: "center" });
    s.addText("【备用做法】", { placeholder: "body", fontSize: 40 }); }
}
D.write(OUT, { loopMs: CHECKIN ? 15000 : 0 });
