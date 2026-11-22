#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""学习通答题 bsk 封装脚本。

把 BrowserSkill CLI 的重复调用封装成命名子命令，内置 iframe 定位、鼠标事件、
UEditor 填写、提交确认等 JS 原语。所有 bsk 调用统一注入 PATH / BSK_AUTO_START=0，
页面变化后自动 cooperate sync。

用法示例：
    python bskq.py session-up
    python bskq.py frames
    python bskq.py read --keyword 章节测验
    python bskq.py radio 0 A
    python bskq.py check 0 0,2,3
    python bskq.py fill 0 "答案一" "答案二"
    python bskq.py submit 0
    python bskq.py score 0
    python bskq.py eval "(function(){return document.title})()"

约定：绝不把学校名、用户名、课程 token 写入任何文件；截图只写系统临时目录，
用完由调用方当场删除。详细规则见 ../references/answer-policy.md。
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

HOME = os.path.expanduser("~")
BSK = os.path.join(HOME, ".local", "bin", "bsk.exe")
if not os.path.isfile(BSK):
    BSK = "bsk"  # 回退到 PATH

ENV = os.environ.copy()
ENV["BSK_AUTO_START"] = "0"
LOCAL_BIN = os.path.join(HOME, ".local", "bin")
ENV["PATH"] = LOCAL_BIN + os.pathsep + ENV.get("PATH", "")

SID_FILE = os.path.join(tempfile.gettempdir(), "chaoxing_b-sk_sid")

# ---- JS 原语（唯一维护处；与 references/dom-and-js.md 保持一致） ----
JS_FIND_FRAMES = r"""
function findFrames(d){ const out=[]; for(const f of d.querySelectorAll('iframe')){
  try{ const dd=f.contentDocument||f.contentWindow.document; if(dd){
    if(f.id==='frame_content') out.push(dd); out.push(...findFrames(dd));
  }}catch(e){} } return out; }
"""

JS_FIRE = r"""
function fire(el,W){ W=W||el.ownerDocument.defaultView; const r=el.getBoundingClientRect();
  const cx=r.left+r.width/2, cy=r.top+r.height/2;
  for(const t of ['pointerdown','mousedown','pointerup','mouseup','click'])
    el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:W,clientX:cx,clientY:cy,button:0})); }
"""

PRELUDE = JS_FIND_FRAMES + JS_FIRE


def run_bsk(args, timeout=90):
    """执行 bsk 子命令，返回 (returncode, stdout+stderr)。"""
    try:
        p = subprocess.run(
            [BSK] + args,
            env=ENV,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except FileNotFoundError:
        return 127, "bsk not found: " + BSK
    except subprocess.TimeoutExpired:
        return 124, "bsk command timed out: " + " ".join(args[:3])
    out = p.stdout.decode("utf-8", "replace")
    err = p.stderr.decode("utf-8", "replace")
    return p.returncode, (out + (("\n[stderr] " + err) if err.strip() else "")).strip()


def load_sid(explicit=None):
    if explicit:
        return explicit
    if os.path.isfile(SID_FILE):
        with open(SID_FILE, "r", encoding="ascii") as f:
            return f.read().strip()
    return None


def save_sid(sid):
    with open(SID_FILE, "w", encoding="ascii") as f:
        f.write(sid.strip())


def require_sid(args):
    sid = load_sid(getattr(args, "session", None))
    if not sid:
        print("ERROR: 未找到会话 id。先运行 `python bskq.py session-up`，或用 --session 指定。", file=sys.stderr)
        sys.exit(2)
    return sid


def sync(sid):
    """页面变化后同步控制上下文；忽略返回内容。"""
    run_bsk(["cooperate", "sync", "--session", sid], timeout=30)


def evaluate(sid, js, do_sync=True, timeout=90):
    """注入 JS 并返回 bsk 输出（已去掉 unverified 提示行）。

    把原语函数与调用表达式统一包进一个 IIFE，并用 return 显式取值。
    这样无论 bsk 内部用 eval 还是 new Function 包装，都能拿到返回值。
    """
    if do_sync:
        sync(sid)
    body = js.strip().rstrip(";")
    wrapped = "(function(){\n" + PRELUDE + "\nreturn (" + body + ");\n})()"
    rc, out = run_bsk(
        ["evaluate", "--session", sid, "--unverified", wrapped],
        timeout=timeout,
    )
    lines = [ln for ln in out.splitlines() if not ln.startswith("note: ran unverified")]
    return rc, "\n".join(lines).strip()


def emit(rc, out):
    print(out)
    if rc != 0:
        sys.exit(rc)


# ---- 子命令实现 ----

def cmd_session_up(args):
    rc, out = run_bsk(["session", "start", "--no-focus", "--json"], timeout=60)
    if rc != 0:
        emit(rc, out)
        return
    sid = None
    try:
        data = json.loads(out.strip().splitlines()[-1])
        sid = data.get("session_id") or data.get("id") or data.get("sessionId")
    except Exception:
        pass
    if not sid:
        # 从输出里抓取 4 字母 id 作为兜底
        import re
        m = re.search(r"\b([a-z]{4})\b", out)
        sid = m.group(1) if m else None
    if not sid:
        print("ERROR: 无法从输出解析 session id，请检查 bsk 输出：\n" + out, file=sys.stderr)
        sys.exit(1)
    save_sid(sid)
    print("SESSION " + sid)
    print("（会话 id 已写入临时文件，后续子命令会自动读取；结束时运行 session-down 清理。）")


def cmd_session_down(args):
    sid = require_sid(args)
    rc, out = run_bsk(["session", "stop", sid], timeout=60)
    if os.path.isfile(SID_FILE):
        os.remove(SID_FILE)
    emit(rc, out)


def cmd_doctor(args):
    for cmd in (["--version"], ["doctor"], ["browsers"]):
        rc, out = run_bsk(cmd, timeout=60)
        print("$ bsk " + " ".join(cmd))
        print(out)
        print()
        if rc != 0 and cmd == ["doctor"]:
            sys.exit(rc)


def cmd_frames(args):
    sid = require_sid(args)
    js = r"""
(() => {
  const docs = findFrames(document);
  const out = docs.map((d,i) => {
    const t = d.body ? d.body.innerText : '';
    return i + ' | len=' + t.length + ' | ' + t.replace(/\s+/g,' ').slice(0,160);
  });
  return out.join('\n') || 'NO frame_content';
})()
"""
    rc, out = evaluate(sid, js)
    emit(rc, out)


def cmd_read(args):
    sid = require_sid(args)
    fi = str(args.frame_index) if args.frame_index is not None else "null"
    key = json.dumps(args.keyword or "", ensure_ascii=False)
    js = r"""
(() => {
  const docs = findFrames(document);
  let idx = __FI__;
  if(idx === null){
    const key = __KEY__;
    if(key){ for(let i=0;i<docs.length;i++){ const t=docs[i].body?docs[i].body.innerText:'';
      if(t.includes(key)){ idx=i; break; } } }
    if(idx === null) idx = 0;
  }
  if(!docs[idx]) return 'NO FRAME idx='+idx+' total='+docs.length;
  const doc = docs[idx];
  const radios = [...doc.querySelectorAll('span.num_option')].map((e,i)=>({
    i, data:e.dataset.data||e.getAttribute('data'), text:(e.innerText||'').trim(),
    picked:(e.className||'').includes('check_answer')
  }));
  const multis = [...doc.querySelectorAll('li.before-after-checkbox')].map((e,i)=>({
    i, text:(e.innerText||'').trim().replace(/\s+/g,' ').slice(0,80),
    picked:!!(e.querySelector('.check_answer_dx'))
  }));
  const editors = [...doc.querySelectorAll('iframe[id^="ueditor_"]')].map(e=>e.id);
  return JSON.stringify({frame_index:idx, total_frames:docs.length,
    radios, multis, editors, text:(doc.body?doc.body.innerText:'').slice(0,6000)});
})()
""".replace("__FI__", fi).replace("__KEY__", key)
    rc, out = evaluate(sid, js)
    emit(rc, out)


def cmd_radio(args):
    sid = require_sid(args)
    fi = args.frame_index
    val = json.dumps(args.value, ensure_ascii=False)
    js = r"""
(() => {
  const doc = findFrames(document)[__FI__];
  if(!doc) return 'NO FRAME __FI__';
  const el = doc.querySelector("span.num_option[data='" + __VAL__ + "']");
  if(!el) return 'NO OPTION ' + __VAL__;
  fire(el, doc.defaultView);
  return 'clicked ' + (el.dataset.data||__VAL__) + ' class=' + el.className;
})()
""".replace("__FI__", str(fi)).replace("__VAL__", val)
    rc, out = evaluate(sid, js)
    emit(rc, out)


def cmd_check(args):
    sid = require_sid(args)
    fi = args.frame_index
    idxs = json.dumps([int(x) for x in args.indices.split(",") if x.strip() != ""])
    js = r"""
(() => {
  const doc = findFrames(document)[__FI__];
  if(!doc) return 'NO FRAME __FI__';
  const lis = [...doc.querySelectorAll('li.before-after-checkbox')];
  const out = [];
  for(const i of __IDXS__){ if(lis[i]){ lis[i].click(); out.push(i); } else out.push('MISS:'+i); }
  return 'clicked ' + out.join(',');
})()
""".replace("__FI__", str(fi)).replace("__IDXS__", idxs)
    rc, out = evaluate(sid, js)
    emit(rc, out)


def cmd_fill(args):
    sid = require_sid(args)
    fi = args.frame_index
    answers = json.dumps(args.answers, ensure_ascii=False)
    js = r"""
(() => {
  const doc = findFrames(document)[__FI__];
  if(!doc) return 'NO FRAME __FI__';
  const W = doc.defaultView;
  if(!W.UE || !W.UE.instants) return 'NO UE INSTANTS';
  const answers = __ANS__;
  const out = [];
  answers.forEach((a,i)=>{
    const ue = W.UE.instants['ueditorInstant'+i];
    if(ue){ ue.setContent(a); out.push(i+':ok len='+a.length); }
    else out.push(i+':NO UE');
  });
  return out.join(' | ');
})()
""".replace("__FI__", str(fi)).replace("__ANS__", answers)
    rc, out = evaluate(sid, js)
    emit(rc, out)


def cmd_save(args):
    sid = require_sid(args)
    fi = args.frame_index
    js = r"""
(() => {
  const doc = findFrames(document)[__FI__];
  if(!doc) return 'NO FRAME __FI__';
  try{ const r = doc.defaultView.noSubmit();
    return 'noSubmit=' + (r===undefined?'(undefined)':String(r)); }
  catch(e){ return 'ERR ' + e.message; }
})()
""".replace("__FI__", str(fi))
    rc, out = evaluate(sid, js)
    emit(rc, out)


def cmd_confirm(args):
    sid = require_sid(args)
    js = r"""
(() => {
  const d = top.document; let tgt = null;
  d.querySelectorAll('a,button,div,span').forEach(el=>{
    const t = (el.innerText||'').trim();
    if(t !== '提交') return;
    const r = el.getBoundingClientRect();
    if(r.width <= 0 || r.height <= 0) return;
    if(el.closest('[class*=mask],[class*=dialog],[class*=Dialog],[class*=layer],.popBottom')) tgt = el;
    else if(!tgt) tgt = el;
  });
  if(!tgt) return 'no target';
  fire(tgt, top);
  return 'clicked 提交 class=' + tgt.className + ' parent=' + (tgt.parentElement ? tgt.parentElement.className : '');
})()
"""
    # fire 在 PRELUDE 中定义；这里用 top 作为 view
    rc, out = evaluate(sid, js)
    emit(rc, out)


def cmd_submit(args):
    sid = require_sid(args)
    fi = args.frame_index
    js = r"""
(() => {
  const doc = findFrames(document)[__FI__];
  if(!doc) return 'NO FRAME __FI__';
  try{ const r = doc.defaultView.btnBlueSubmit();
    return 'btnBlueSubmit=' + (r===undefined?'(undefined)':String(r)); }
  catch(e){ return 'ERR ' + e.message; }
})()
""".replace("__FI__", str(fi))
    rc, out = evaluate(sid, js)
    print(out)
    if rc != 0:
        sys.exit(rc)
    # btnBlueSubmit 后主文档弹确认框，再做一次同步并点「提交」
    sync(sid)
    js2 = r"""
(() => {
  const d = top.document; let tgt = null;
  d.querySelectorAll('a,button,div,span').forEach(el=>{
    const t = (el.innerText||'').trim();
    if(t !== '提交') return;
    const r = el.getBoundingClientRect();
    if(r.width <= 0 || r.height <= 0) return;
    if(el.closest('[class*=mask],[class*=dialog],[class*=Dialog],[class*=layer],.popBottom')) tgt = el;
    else if(!tgt) tgt = el;
  });
  if(!tgt) return 'CONFIRM no target';
  fire(tgt, top);
  return 'CONFIRM clicked class=' + tgt.className + ' parent=' + (tgt.parentElement ? tgt.parentElement.className : '');
})()
"""
    rc2, out2 = evaluate(sid, js2, do_sync=False)
    emit(rc2, out2)


def cmd_score(args):
    sid = require_sid(args)
    fi = args.frame_index
    js = r"""
(() => {
  const doc = findFrames(document)[__FI__];
  if(!doc) return 'NO FRAME __FI__';
  const t = doc.body ? doc.body.innerText : '';
  const m = t.match(/最终成绩\s*(\d+(?:\.\d+)?)\s*分/);
  let out = m ? ('SCORE ' + m[1]) : 'NO SCORE';
  const lines = t.split('\n');
  const wrong = [];
  for(let i=0;i<lines.length;i++){
    if(lines[i].includes('0.0分')){
      let corr = '';
      for(let j=i+1;j<lines.length && j<i+4;j++){
        if(lines[j].includes('正确答案')){ corr = (lines[j]+' '+(lines[j+1]||'')).replace(/\s+/g,' ').slice(0,80); break; }
      }
      wrong.push(corr);
    }
  }
  if(wrong.length) out += '\nWRONG ' + wrong.join(' | ');
  return out;
})()
""".replace("__FI__", str(fi))
    rc, out = evaluate(sid, js)
    emit(rc, out)


def cmd_shot(args):
    sid = require_sid(args)
    out_path = args.out or os.path.join(tempfile.gettempdir(), "chaoxing_quiz_shot.png")
    rc, out = run_bsk(["screenshot", "--session", sid, "--out", out_path], timeout=90)
    print(out)
    print("SHOT " + out_path)
    print("提醒：查看后当场删除该截图（rm -f），不要留存。")
    if rc != 0:
        sys.exit(rc)


def cmd_eval(args):
    sid = require_sid(args)
    rc, out = evaluate(sid, args.javascript)
    emit(rc, out)


def build_parser():
    p = argparse.ArgumentParser(
        prog="bskq.py",
        description="学习通答题 bsk 封装：命名子命令 + 内置 JS 原语，杜绝重复手拼 evaluate。",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_session(sp):
        sp.add_argument("--session", default=None, help="会话 id；省略则读临时文件")

    s = sub.add_parser("session-up", help="新建会话并记录 id")
    s.set_defaults(func=cmd_session_up)

    s = sub.add_parser("session-down", help="结束会话并清理 id")
    add_session(s)
    s.set_defaults(func=cmd_session_down)

    s = sub.add_parser("doctor", help="bsk 版本 / doctor / browsers 自检")
    s.set_defaults(func=cmd_doctor)

    s = sub.add_parser("frames", help="列出所有 frame_content 摘要")
    add_session(s)
    s.set_defaults(func=cmd_frames)

    s = sub.add_parser("read", help="结构化读取题目与选项")
    add_session(s)
    s.add_argument("frame_index", type=int, nargs="?", default=None, help="frame 序号；省略靠 --keyword 或默认 0")
    s.add_argument("--keyword", default=None, help="按 innerText 关键词选 frame")
    s.set_defaults(func=cmd_read)

    s = sub.add_parser("radio", help="单选/判断作答")
    add_session(s)
    s.add_argument("frame_index", type=int)
    s.add_argument("value", help="选项值，如 A / B / true / false")
    s.set_defaults(func=cmd_radio)

    s = sub.add_parser("check", help="多选作答")
    add_session(s)
    s.add_argument("frame_index", type=int)
    s.add_argument("indices", help="逗号分隔的选项序号，如 0,2,3")
    s.set_defaults(func=cmd_check)

    s = sub.add_parser("fill", help="填空/简答填写（UEditor）")
    add_session(s)
    s.add_argument("frame_index", type=int)
    s.add_argument("answers", nargs="+", help="按题号顺序的答案文本")
    s.set_defaults(func=cmd_fill)

    s = sub.add_parser("save", help="暂时保存（noSubmit），仅用户明确要求时用")
    add_session(s)
    s.add_argument("frame_index", type=int)
    s.set_defaults(func=cmd_save)

    s = sub.add_parser("confirm", help="单独点主文档确认弹窗的「提交」")
    add_session(s)
    s.set_defaults(func=cmd_confirm)

    s = sub.add_parser("submit", help="提交（btnBlueSubmit + 确认弹窗）")
    add_session(s)
    s.add_argument("frame_index", type=int)
    s.set_defaults(func=cmd_submit)

    s = sub.add_parser("score", help="读最终成绩与错题依据")
    add_session(s)
    s.add_argument("frame_index", type=int)
    s.set_defaults(func=cmd_score)

    s = sub.add_parser("shot", help="截图到临时目录（用完即删）")
    add_session(s)
    s.add_argument("--out", default=None, help="输出路径；默认系统临时目录")
    s.set_defaults(func=cmd_shot)

    s = sub.add_parser("eval", help="逃生舱：注入任意 JS（返回值需自己 return）")
    add_session(s)
    s.add_argument("javascript", help="JS 表达式/IIFE")
    s.set_defaults(func=cmd_eval)

    return p


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
