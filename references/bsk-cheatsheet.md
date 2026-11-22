# bsk 命令速查（BrowserSkill CLI）

`bsk` 是腾讯 BrowserSkill 的 CLI，通常安装在 `$HOME/.local/bin/bsk.exe`（v0.5.0，Windows）。它通过 daemon + Edge 扩展接管浏览器，点击注入是独立实现，能绕开扩展自身 `cua_click` 超时的问题。

以下语法已用真实 `bsk --help` 校准。不确定某个子命令的参数时，先跑 `bsk <子命令> --help`，不要硬编码。

## 0. 通用前缀

每条命令都带：

```bash
export PATH="$HOME/.local/bin:$PATH"; export BSK_AUTO_START=0; <bsk 命令> 2>&1
```

- `BSK_AUTO_START=0` 避免自动拉起额外 daemon。
- Windows / Git Bash 下若 PATH 未生效，直接用绝对路径 `"$HOME/.local/bin/bsk.exe"`。

## 1. 环境与自检

| 命令 | 用途 |
|---|---|
| `bsk --version` | 版本确认 |
| `bsk doctor` | 6 项自检：bsk home / daemon / 进程身份 / 协议 / 自动更新 / 扩展连接 / 本地连接。全绿且退出码 0 才可用 |
| `bsk status --json` | daemon pid 与浏览器连接状态 |
| `bsk browsers` | 列出已连接浏览器（确认 Edge 扩展在线） |

## 2. daemon 与会话

```bash
# 后台常驻（监听 ws://127.0.0.1:52800）
bsk daemon start --foreground

# 开会话，返回随机 4 字母 id（记作 $SID）
bsk session start --no-focus --json

# 会话管理
bsk session list
bsk session stop <SID>
```

`session stop` + `session start` 是控制上下文卡死后的标准恢复动作。

## 3. 控制上下文（关键规则）

**页面变化后，任何 evaluate / navigate 之前必须先同步：**

```bash
bsk cooperate sync --session <SID>            # 返回 observation_id / context_id / revision / tab_id
bsk cooperate sync --session <SID> >/dev/null 2>&1   # 静默同步，常用于 evaluate 前
bsk cooperate wait --session <SID>            # 等待 busy frame 恢复
```

不同步会报：`the control context no longer belongs to the current document or control state ... requires a valid control context from cooperate sync`。

## 4. 导航与观察

```bash
# 基础导航
bsk navigate --session <SID> "<url>"

# 需要 observation 时（先取 id）
OBS=$(bsk cooperate sync --session <SID> | python -c "import sys,json; print(json.load(sys.stdin)['observation_id'])")
bsk navigate --session <SID> --observation "$OBS" "<url>"

# 观察（VOM 快照，iframe 内容会被平铺，元素带 @eN ref）
bsk observe --session <SID> --json 2>&1 | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('text','')[:4000])"

# 更细的 aria 快照
bsk snapshot --session <SID>
```

`observe` 输出形如 `@vom 1 / @view 764x573 / L1 page / RootWebArea "学生学习页面"`，可直接拿 `@e153` 这类 ref 去点击。

## 5. 执行 JS / 点击 / 滚动 / 截图

```bash
bsk evaluate --session <SID> --unverified "<JS 表达式>"
bsk click --session <SID> --ref "@e153"
bsk click --session <SID> --selector "span.num_option[data='A']"   # 仅主 frame 生效
bsk click --session <SID> --image-x 156 --image-y 298
bsk scroll --session <SID> --dy 800
bsk scroll-to --session <SID> --ref "@e143"
bsk screenshot --session <SID> --out /tmp/xxx.png                  # 用完即删
bsk network --session <SID> --json                                 # 抓网络请求，排查用
```

- `--unverified` 跳过与 observation 比对，速度优先，输出末尾固定提示 `note: ran unverified; ...`。
- iframe 内的元素不要用 `bsk click --selector`（只作用主 frame），改用 `bsk evaluate` 注入 JS。

## 6. 解析输出的一行式

多数命令支持 `--json`，配合 python 提取字段：

```bash
bsk session start --no-focus --json | python -c "import sys,json; print(json.load(sys.stdin)['session_id'])"
bsk observe --session <SID> --json | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('text','')[:4000])"
```

字段名以实际 JSON 为准，先原样跑一次看结构。

## 7. 路径与编码注意

- Windows Git Bash 下路径用 `/c/Users/...` 或 `C:/Users/...`；写 JS 时避免在双引号里嵌套未转义的引号。
- 复杂 JS 建议放进 `bskq.py` 的常量，通过 `bskq.py eval` 调用，减少 shell 引号地狱。
- 不要持久化 bsk 日志：日志里的 URL 可能含课程 token。
