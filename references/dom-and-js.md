# 学习通 DOM 结构与 JS 原语

本文件是答题相关 DOM 选择器与 JavaScript 代码的**唯一存储处**。`scripts/bskq.py` 内置这些原语；本文件供适配新题型、排查失效、以及 `eval` 逃生舱时参考。

## 1. 页面结构

学习通学生学习页的题目藏在**多层 iframe** 里，题目最终位于 `id="frame_content"` 的 iframe：

```
主文档 document
  └─ iframe (目录 / 外层容器)
       └─ ... 可能多层 ...
            └─ iframe#frame_content   ← 题目、选项、提交按钮在这里
```

- 一个页面可能有**多个** `frame_content`（例如「研讨问题1」「研讨问题2」「章节测验」并列）。用 `body.innerText` 关键词（如「章节测验」「随堂练习」）区分，或用 `bsk observe` 的 `@eN` ref 定位后再取对应 frame。
- 目录树在顶层 iframe 中，节点容器 class 为 `div.posCatalog_select`，其 `id` 即该章节的 `chapterId`。
- 跳转章节的 URL 形态（**只写参数名，禁止写入任何真实值**）：
  `https://mooc1.chaoxing.com/mycourse/studentstudy?chapterId=<ID>&courseId=<ID>&clazzid=<ID>&cpi=<ID>&enc=<TOKEN>&mooc2=1`
  同一课程内只改 `chapterId` 即可切章；其余参数沿用当前页面。

## 2. DOM 选择器映射表

| 目标 | 选择器 / 位置 | 判定与操作 |
|---|---|---|
| 题目容器 | `iframe#frame_content` | 递归收集；可能多个，按 innerText 关键词选 |
| 单选 / 判断选项 | `span.num_option`，外层 `label.fl.before`，`data="A"`/`"B"`/`"true"`/`"false"` | 选中后 class 增加 `check_answer`；**`.click()` 无效**，必须派发完整鼠标事件序列 |
| 多选选项 | `li.before-after-checkbox`，内含 `span.num_option_dx`，`onclick="addMultipleChoice(this)"` | 选中后 class 增加 `check_answer_dx`；**`.click()` 即可** |
| 填空 / 简答输入 | UEditor iframe `id="ueditor_0..N"`，实例 `UE.instants['ueditorInstant0..N']` | 用 `ue.setContent(answer)` 填入（官方 API，能正确同步）；用 `ue.getContent()` 验证 |
| 暂时保存按钮 | `.btnSave`，`onclick="noSubmit()"` | 仅用户明确要求时使用 |
| 提交按钮 | `.btnSubmit`，`onclick="btnBlueSubmit()"` | 调用 `W.btnBlueSubmit()`，返回 undefined 属正常 |
| 确认弹窗「提交」 | 主文档中可见文字为「提交」的元素（实测 class `jb_btn`，父级 `.popBottom`） | 在 `[class*=mask],[class*=dialog],[class*=layer],.popBottom` 内找可见元素并派发鼠标事件 |
| 最终成绩 | frame body.innerText 中「最终成绩 XX 分」 | 正则提取分数 |
| 错题依据 | frame body.innerText 中「我的答案」「正确答案」 | 用于反推混淆题干、积累还原经验 |

## 3. JS 原语

### 3.1 递归收集所有 `frame_content`

```js
function findFrames(d){ const out=[]; for(const f of d.querySelectorAll('iframe')){
  try{ const dd=f.contentDocument||f.contentWindow.document; if(dd){
    if(f.id==='frame_content') out.push(dd); out.push(...findFrames(dd));
  }}catch(e){} } return out; }
```

调用：`const docs=findFrames(document);` 得到数组，按 `docs[i].body.innerText` 选目标。

### 3.2 递归列出 iframe 树（调试用）

```js
(() => { function walk(d, depth){ let out=[]; for(const fr of d.querySelectorAll('iframe')){
  out.push('DEPTH'+depth+' src='+fr.src+' id='+fr.id);
  try{ const dd=fr.contentDocument||fr.contentWindow.document;
    if(dd){ const t=dd.body?dd.body.innerText:'';
      out.push('  len='+t.length+' preview='+t.slice(0,120).replace(/\n/g,' '));
      out.push(...walk(dd, depth+1)); }
  }catch(e){ out.push('  ERR '+e.message); } }
  return out; } return walk(document,0).join('\n'); })()
```

### 3.3 完整鼠标事件序列 `fire`（单选/判断/确认弹窗必用）

```js
function fire(el,W){ W=W||el.ownerDocument.defaultView; const r=el.getBoundingClientRect();
  const cx=r.left+r.width/2, cy=r.top+r.height/2;
  for(const t of ['pointerdown','mousedown','pointerup','mouseup','click'])
    el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:W,clientX:cx,clientY:cy,button:0})); }
```

说明：学习通单选用 JS `.click()` 不触发，必须派发上述 5 个事件。多选 `li.before-after-checkbox` 用 `.click()` 即可。

### 3.4 单选 / 判断作答

```js
(() => {
  function findFrames(d){ /* 见 3.1 */ }
  const doc=findFrames(document)[FRAME_INDEX];   // FRAME_INDEX 由脚本注入
  const W=doc.defaultView;
  const el=doc.querySelector("span.num_option[data='VALUE']"); // VALUE 由脚本注入，如 A / true
  if(!el) return 'NO OPTION';
  const r=el.getBoundingClientRect();
  const cx=r.left+r.width/2, cy=r.top+r.height/2;
  for(const t of ['pointerdown','mousedown','pointerup','mouseup','click'])
    el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:W,clientX:cx,clientY:cy,button:0}));
  return 'clicked '+el.dataset.data+' class='+el.className;
})()
```

核对是否选中：检查对应 `span.num_option` 的 className 是否含 `check_answer`。

### 3.5 多选作答

```js
(() => {
  const doc=findFrames(document)[FRAME_INDEX];
  const lis=[...doc.querySelectorAll('li.before-after-checkbox')];
  const picked=[];
  for(const i of [INDEX_LIST]){ if(lis[i]){ lis[i].click(); picked.push(i); } }
  return 'clicked '+picked.join(',');
})()
```

核对：对应 `span.num_option_dx` 的 className 含 `check_answer_dx`。

### 3.6 填空 / 简答填写（UEditor 官方 API）

```js
(() => {
  const docs=findFrames(document);
  // 用关键词选定目标 quiz frame，例如：docs.forEach(dd=>{ if(dd.body.innerText.includes('关键词')) quiz=dd; })
  const W=quiz.defaultView;
  const answers=[ /* 按题号顺序 */ ];
  const out=[];
  answers.forEach((a,i)=>{
    const ue=W.UE.instants['ueditorInstant'+i];
    if(ue){ ue.setContent(a); out.push(i+':ok len='+a.length); }
    else out.push(i+':NO UE');
  });
  return out.join(' | ');
})()
```

注意：不要直接改 iframe 内 `[contenteditable=true]` 的 `innerHTML`，学习通可能不认。始终用 `UE.instants[...].setContent()`。多 frame 时实例编号要和目标 quiz frame 对应。

### 3.7 提交与确认弹窗

```js
// 第一步：触发提交（在 quiz frame 内）
(() => { const doc=findFrames(document)[FRAME_INDEX];
  try{ const r=doc.defaultView.btnBlueSubmit(); return 'btnBlueSubmit='+(r===undefined?'(undefined)':String(r)); }
  catch(e){ return 'ERR '+e.message; } })()
```

```js
// 第二步：点主文档确认弹窗的「提交」（btnBlueSubmit 之后）
(() => {
  const d=top.document; let tgt=null;
  d.querySelectorAll('a,button,div,span').forEach(el=>{
    const t=(el.innerText||'').trim();
    if(t!=='提交') return;
    const r=el.getBoundingClientRect(); if(r.width<=0||r.height<=0) return;
    if(el.closest('[class*=mask],[class*=dialog],[class*=Dialog],[class*=layer],.popBottom')) tgt=el;
    else if(!tgt) tgt=el;
  });
  if(!tgt) return 'no target';
  const r=tgt.getBoundingClientRect();
  const cx=r.left+r.width/2, cy=r.top+r.height/2;
  for(const t of ['pointerdown','mousedown','pointerup','mouseup','click'])
    tgt.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:top,clientX:cx,clientY:cy,button:0}));
  return 'clicked 提交 at '+Math.round(cx)+','+Math.round(cy)+' class='+tgt.className;
})()
```

### 3.8 读成绩与错题

```js
(() => {
  const doc=findFrames(document)[FRAME_INDEX];
  const t=doc.body.innerText;
  const m=t.match(/最终成绩\s*(\d+(?:\.\d+)?)\s*分/);
  return m ? ('SCORE '+m[1]) : 'NO SCORE';
})()
```

错题反推（可选，用于积累还原经验）：

```js
(() => { const doc=findFrames(document)[FRAME_INDEX];
  const lines=doc.body.innerText.split('\n'); let out=[];
  for(let i=0;i<lines.length;i++){
    if(lines[i].includes('0.0分')){
      let q=''; for(let j=i-1;j>=0&&j>i-25;j--){ if(/^\d+$/.test(lines[j].trim())){ q=lines[j].trim(); break; } }
      let corr=''; for(let j=i+1;j<lines.length&&j<i+4;j++){ if(lines[j].includes('正确答案')){ corr=lines[j]+' '+(lines[j+1]||''); break; } }
      out.push('题'+q+' '+corr.replace(/\s+/g,' ').slice(0,90));
    }
  } return out.join('\n')||'没有0分题'; })()
```

## 4. 逃生舱 `eval`

新题型或改版导致脚本失效时，用 `bskq.py eval '<js>'` 直接注入任意 JS。约定：

- 脚本里始终先 `bsk cooperate sync` 再 evaluate（页面变化后控制上下文会失效）。
- 新验证有效的模式，回写进本文件和 `bskq.py`，避免每次重新组装。
- 同一处 JS 只在 `dom-and-js.md` 和脚本常量中维护，禁止散落到对话外的临时文件。
