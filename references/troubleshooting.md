# 故障排查

按现象查表，按顺序尝试；每步操作后重新验证再决定是否进入下一步。

## 1. bsk 控制上下文卡死（最常见）

**现象**：`evaluate` 报 `mode: unavailable`、`state: {editing:false, mode:"unavailable"}`、`shared page control or observation changed`、多个 frame 无响应，或 `bsk cooperate sync` 输出非 JSON。

**原因**：短时间内大量 DOM 操作（连续 evaluate、批量点击）让控制上下文失效。

**处理顺序**：
1. `bsk cooperate wait --session <SID>` 等 busy frame 恢复。
2. `bsk cooperate sync --session <SID>` 重新同步。
3. 仍失败则重启会话：`bsk session stop <SID> && bsk session start --no-focus --json`，重新导航回当前章节。
4. 预防：**分批作答**——先把多选题做完，再处理判断/单选，最后简答；每批之间给页面喘息。避免一次 evaluate 操作几十道题。

## 2. 导航后报错「control context no longer belongs to current document」

**现象**：`bsk navigate` 或 evaluate 报控制上下文不属于当前文档。

**原因**：URL 变化后没重新同步。

**处理**：导航前先 `bsk cooperate sync`，需要时取 `observation_id` 传给 `bsk navigate --observation "$OBS"`。

## 3. Edge 扩展点击超时（看得到、点不到）

**现象**：`cua_click`、`dom_cua_get_visible_dom` 发出后不回包直到超时；但截图、滚动、按键、跳转、读页都正常。

**原因**：扩展自身点击注入的 bug（0.2.8 曾出现），刷新、重接管、新标签、F5 均无效。

**处理**：不要再用扩展的 `cua_*` 工具，改用 `bsk`（其点击是独立的事件注入实现）。本 skill 全程走 bsk，不走扩展点击。

## 4. 提交后 iframe 仍显示「待完成」

**现象**：`btnBlueSubmit()` 和确认弹窗都点了，但 frame 内文本缓存还写着「待完成」，看起来像没提交。

**处理**：
1. 不要重读 iframe 缓存文本下结论。
2. 用 `shot` 截图看目录树的章节标记——绿色完成标记 + 页面「最终成绩」才是判据。
3. 确实没变化时，再重新触发一次提交 + 确认，然后以截图和成绩为准。

## 5. 单选点击无效

**现象**：`span.num_option` 上 `.click()` 后 `check_answer` class 没出现。

**原因**：学习通单选绑定的是真实鼠标事件，`click()` 合成事件不触发。

**处理**：用 `fire()` 派发 `pointerdown/mousedown/pointerup/mouseup/click` 五个事件（见 `dom-and-js.md` 3.3）。多选 `li.before-after-checkbox` 用 `.click()` 即可，别混用。

## 6. UEditor 填空填不进去

**现象**：改了 `[contenteditable=true]` 的 `innerHTML`，提交后该题 0 分或空白。

**原因**：学习通只认 UEditor 实例的内部状态，直接改 DOM 不回写。

**处理**：用 `W.UE.instants['ueditorInstant'+i].setContent(answer)`，并用 `getContent()` 验证。注意多 frame 时实例编号与目标 quiz frame 对应。

## 7. 会话/页面突然断开

**现象**：浏览器连接还在但会话没了、页面关闭、`No tab with id`、换模型或关掉 Agent 小窗口后断线。

**处理**：
1. 提醒用户**不要手动关闭带 BrowserSkill/Agent 的小窗口**。
2. `bsk browsers` / `bsk session list` 确认扩展在线。
3. 重开 session 并导航回当前章节继续。已暂存的草稿不会丢；未暂存且未提交的当章需要重答。

## 8. bsk 安装 / 下载失败

**现象**：GitHub release 直连返回 502 / `schannel: server closed abruptly`。

**处理**：
- 用镜像：`https://ghproxy.net/https://github.com/Tencent/BrowserSkill/releases/download/<tag>/<asset>`。
- 后台下载 + 断点续传：`curl -fL --connect-timeout 20 --max-time 500 --retry 3 --retry-all-errors -C - -o bsk.zip "<镜像URL>"`。
- 校验 sha256：`1bba7cd6d771df48485c396b8d5f1e06f9bc93cd648b0552013c30f90aeaaa40`（对应 v0.5.0 Windows x86_64）。
- 校验通过再解压到 `~/.local/bin/`。本机已装好，通常跳过。

## 9. 混淆题干还原不出来

**现象**：题干被形近生僻字替换，WebSearch 搜不到。

**处理**：见 `answer-policy.md` 2.2。从题干里未混淆的字反推 + 领域知识还原 + 查权威依据；仍无把握加入「不确定清单」集中问用户，**不要硬猜**。
