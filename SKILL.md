---
name: chaoxing-auto-quiz
display_name_zh: 学习通自动答题
description: 用 bsk 浏览器自动化完成超星学习通（mooc1.chaoxing.com）章节测验、随堂练习与作业答题：定位章节、逐题读取、查证作答、默认直接提交并读取最终成绩。当用户说"帮我做学习通任务点""继续答题""做章节测验""把学习通作业答了""学习通答题""把这个任务点刷完"时使用。仅在浏览器会话内操作，不保存学校名/用户名，截图用完即删。
description_en: Automate Chaoxing (chaoxing.com) chapter quizzes and homework via the bsk browser CLI, with answer verification and direct submission.
agent_created: true
version: 1.0.0
---

# 学习通自动答题

用 bsk（BrowserSkill CLI）接管本机 Edge，读取学习通章节测验并逐题作答。只自动化**答题**部分：登录、验证码、看视频、签到、讨论由用户人工完成。仅限用户自己的账号与课程。

下文所有 `bskq.py` 调用一律用绝对路径（避免 cwd 问题）。设 skill 目录为 `<SKILL>`（即本文件所在目录，如 `$HOME/.workbuddy/skills/chaoxing-auto-quiz`）：
`python "<SKILL>/scripts/bskq.py" <子命令> [参数]`
简写为 `bskq.py`。

## 1. 硬规则（任何情况下不破）

1. **默认直接提交**：答完一章即提交并读最终成绩。`save`（暂时保存）仅当用户明确说「先保存/暂存」时调用。
2. **不高错误率**：不确定题先 WebSearch 查权威依据、还原混淆题干；仍无把握的集中一次列给用户，不硬猜。详见 `references/answer-policy.md`。
3. **隐私红线**：不把学校名、用户名、学号、真实课程名、含 `enc`/`clazzid`/`cpi` token 的 URL 写入任何文件或记忆；查询不带个人标识；截图当场删除；收尾停会话。详见 `references/answer-policy.md`。
4. **以事实为准**：提交后 iframe 文本可能仍缓存显示「待完成」，以目录绿标 + 最终成绩为准，不轻信缓存。
5. **提交不可撤销**：首次在新课程上使用时，提交前向用户提示一次；同课程后续章节按默认直提。

## 2. 环境自检

```bash
python "<SKILL>/scripts/bskq.py" doctor
```

依次跑 `bsk --version`、`bsk doctor`、`bsk browsers`。要求 doctor 六项全绿、browsers 显示 Edge 扩展在线。失败时按 `references/troubleshooting.md` 处理。命令语法见 `references/bsk-cheatsheet.md`。

## 3. S1 启动会话

```bash
python "<SKILL>/scripts/bskq.py" session-up
```

新建会话并把 id 记入临时文件，后续子命令自动读取。若 daemon 未运行，先按 `references/bsk-cheatsheet.md` 后台启动 `bsk daemon start --foreground`。用户须保持带 BrowserSkill 的 Agent 小窗口开启。

## 4. S2 定位章节

两种路径，任选其一：
- **目录点击**：先 `bsk observe` 读目录里目标章节的 `@eN` ref，再 `bsk click --ref @eN`。
- **URL 跳章**：从目录 DOM `div.posCatalog_select` 的 id 取目标 `chapterId`，只替换当前 URL 的 `chapterId` 参数导航。参数只留在内存，不写文件。

进入后先确认页面标题/章节名与用户要求一致，再开始读题。

## 5. S3 读题

```bash
python "<SKILL>/scripts/bskq.py" frames
python "<SKILL>/scripts/bskq.py" read --keyword 章节测验
```

`frames` 列出所有 `frame_content` 摘要；`read` 输出结构化题目（JSON：各题型选项、已选标记、UEditor 数量、正文）。一页多个 frame 时用 `--keyword` 或序号锁定目标，先核对题目数量与用户可见一致。DOM 细节见 `references/dom-and-js.md`。

## 6. S4 查证与作答

先按 `references/answer-policy.md` 对每题定置信度：高/中档查证后作答，低档进入「不确定清单」。作答命令：

```bash
# 单选/判断：frame 序号 + 选项值（A/B/C/D 或 true/false）
python "<SKILL>/scripts/bskq.py" radio 0 A

# 多选：frame 序号 + 逗号分隔的选项序号（从 0 开始）
python "<SKILL>/scripts/bskq.py" check 0 0,2,3

# 填空/简答：frame 序号 + 按题号顺序的答案文本
python "<SKILL>/scripts/bskq.py" fill 0 "答案一" "答案二"
```

- 分批作答：先多选 → 判断/单选 → 简答，避免大批 DOM 操作导致控制上下文卡死。
- 每批后用 `read` 核对 `picked` 标记确认选中。
- 新题型/改版导致脚本失效时，用 `eval` 逃生舱注入 JS，验证有效后回写 `references/dom-and-js.md` 与 `scripts/bskq.py`。

## 7. S5 不确定题处理

把本章所有低置信度题**一次列给用户**：题号 + 题干还原猜测 + 候选选项 + 已查依据。一轮问完，不要逐题打断。收到回复后批量补答，再进入提交。查证流程与阈值见 `references/answer-policy.md`。

## 8. S6 暂存（可选）

仅用户明确要求时：
```bash
python "<SKILL>/scripts/bskq.py" save 0
```
暂存不消除「待完成」状态、不产生成绩，不要当成提交。

## 9. S7 提交

```bash
python "<SKILL>/scripts/bskq.py" submit 0
```

内部先调 `btnBlueSubmit()`，再在主文档确认弹窗点「提交」。首次在新课程使用时，提交前向用户提示一次；同课程后续章节直提。提交动作不可撤销。

## 10. S8 读成绩与收尾

```bash
python "<SKILL>/scripts/bskq.py" score 0
python "<SKILL>/scripts/bskq.py" session-down
```

`score` 读「最终成绩 XX 分」与错题依据。若成绩异常或无变化，按 `references/troubleshooting.md` 用 `shot` 截图目视确认目录绿标，截图查看后当场删除。收尾核对临时目录无遗留截图，不写任何工作记忆。

## 11. 故障速查

| 现象 | 处理 |
|---|---|
| `mode: unavailable` / 控制上下文失效 | `cooperate wait` 后 sync，不行则 session-down + session-up 重启 |
| 单选点击无效 | 必须用完整鼠标事件序列，`radio` 子命令已内置 |
| 填空填不进 | 用 `UE.instants[...].setContent()`，`fill` 子命令已内置 |
| 提交后仍显示「待完成」 | 以目录绿标 + 最终成绩为准，截图确认 |
| Edge 扩展点击超时 | 全程走 bsk，不用扩展 `cua_*` |
| 会话/页面断开 | 确认扩展在线，重开会话回到当前章节 |

完整排查见 `references/troubleshooting.md`。

## 12. 资源索引

- `references/answer-policy.md` — 查证策略、置信阈值、隐私红线、提交策略（决策唯一来源）
- `references/dom-and-js.md` — DOM 选择器与 JS 原语全文（代码唯一来源）
- `references/bsk-cheatsheet.md` — bsk 命令语法速查
- `references/troubleshooting.md` — 故障排查
- `scripts/bskq.py` — bsk 封装脚本（所有作答/提交命令）
