# chaoxing-auto-quiz

一个面向超星学习通（mooc1.chaoxing.com）的答题辅助 skill。本 skill 用 bsk 接管本机 Edge，读取章节测验与随堂练习的题目，查证后填写选项并提交，最后读取成绩。

## 能力边界

本 skill 只自动化「答题」这一段流程。以下环节一律由使用者人工完成：

- 登录与验证码
- 视频观看进度
- 签到与讨论

本 skill 不绕过验证码，不批量注册，不破解答题接口，不处理他人账号。使用者只能对自己名下的课程使用。

## 隐私设计

本 skill 的一条硬性约束是不落盘任何个人标识，具体包括：

- 学校名、用户名、学号、真实课程名不写入任何文件、临时产物或工作记忆
- URL 中的 `chapterId`、`courseId`、`clazzid`、`cpi`、`enc`、`openc` 等参数只存在于 shell 变量与 bsk 会话内存
- 截图只写入系统临时目录，用完当场删除
- 查询知识点时不拼接学校名或课程名

上述规则在 `references/answer-policy.md` 中有完整表述，`scripts/bskq.py` 的模块注释也做了同样约定。

## 目录结构

```
chaoxing-auto-quiz/
├── SKILL.md                      # 主入口，含 frontmatter
├── references/
│   ├── answer-policy.md          # 答题策略与隐私红线
│   ├── bsk-cheatsheet.md         # bsk CLI 命令速查
│   ├── dom-and-js.md             # 页面结构与 JS 原语
│   └── troubleshooting.md        # 常见故障处理
└── scripts/
    └── bskq.py                   # bsk 调用的命名子命令封装
```

## 安装

从 GitHub 克隆（推荐）：

```bash
git clone https://github.com/gaojibxnzxm/chaoxing-auto-quiz.git ~/.workbuddy/skills/chaoxing-auto-quiz
```

也可以手动把整个文件夹放进 WorkBuddy 的 skills 目录：

```
~/.workbuddy/skills/chaoxing-auto-quiz/
```

Windows 下的完整路径是 `C:\Users\<你的用户名>\.workbuddy\skills\chaoxing-auto-quiz\`。

## 依赖

- Python 3.9 及以上
- bsk（BrowserSkill CLI），需要安装在 `~/.local/bin/` 或加入 `PATH`
- 本机已安装 Edge 浏览器

脚本内部用 `os.path.expanduser("~")` 定位 bsk，不依赖任何绝对路径，更换机器后无需修改代码。

## 使用

在对话中说出类似「帮我做学习通任务点」「做章节测验」「继续答题」的请求即可触发。直接调用脚本的方式见 `SKILL.md` 第 14 行起的说明，其中 `<SKILL>` 指本文件夹所在目录。

## 免责声明

自动化操作可能违反超星平台的服务条款或所在学校的学术规范。使用者应自行判断并承担相应后果，本项目的作者不对使用行为及其结果负责。

## 许可

MIT，详见 `LICENSE`。
