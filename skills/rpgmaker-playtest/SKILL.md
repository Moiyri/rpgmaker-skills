---
name: rpgmaker-playtest
description: 启动或附加 RPG Maker MZ 的 NW.js 游戏，动态查询测试命令、准备测试现场、读档并截图验证。需要游戏内实际测试、复现问题或编写工程专用金手指时使用；内置可选 Debug.js，Python 连接仅使用标准库。
---

# RPG Maker Playtest

使用 Python 3.10+ 标准库客户端，不安装 Playwright 或浏览器。先读取工程约定，确认工程、NW.js 可执行文件与测试目标。实际接口见 scripts/playtest.py、scripts/session.py；[最小测试](examples/load_game.py)。

现有接口、验证边界与待完善事项见[功能清单](references/capabilities.md)。设计测试前按实际能力选择接口，扩展命令名称与参数遵循正式注册规则。

## 选择是否安装 Debug

- 只连接、截图或观察已有页面不需要 Debug。
- 需要动态命令、读档、HUD 或金手指时先检查工程是否已有兼容 Debug。按用户需求安装，不因测试就自动修改插件配置。
- 用户要求这些能力且工程尚无实现时，可安装随附 assets/Debug.js 到 js/plugins/playtest/Debug.js；同名现有文件先核对，不覆盖用户定制。
- 安装、启用、排序、卸载清单均使用[插件技能](../rpgmaker-plugins/SKILL.md)的正式脚本。移除注册与删除源码是两件事。
- Debug 仅在引擎 test 模式启用（NW.js 的 `test` 参数或 `?test`）。普通启动不公开接口、不创建 HUD。反引号显隐、`/` 输入、Escape 退出；命令行目前只回显，不执行命令。

## 事件测试

需要像编辑器一样执行指定地图事件或公共事件的部分指令时，读取[事件测试接口](references/event-test.md)，使用 `scripts/event_test.py` 的 prepare／launch 接口。编号用于读取源指令；Debug 将所选指令赋给 `$testEvent`，调用原版事件测试，在空白地图以事件 ID 0 执行。启动仍传 `test`，读取已保存的数据库；临时配置放在工程外。报告供 agent 分析，用户操作对白与选项。

## 运行时钩子

使用 [Hook 对象接口](references/hooks.md) 配置启动、错误、退出、事件执行和变量／开关变化的观察。Agent 使用 `Hook`、`Hooks` 直接传参；通过 `test.add_hook/list_hooks/remove_hook/clear_hooks` 动态管理，独立于 command。启动前传入 hooks，调用 poll 或分段 wait 收集报告。实现尚未运行验收。

## 自动化测试与用户测试

自动化测试由 agent 预先编写普通 Python 脚本，复用现有 Game、启动接口和 Hook/Hooks：启动游戏 → 执行操作 → 检查预期 → 保存报告 → 关闭游戏，执行结束后由 agent 读取结果。脚本负责运行期间的轮询与等待，agent 不逐步发送操作。沿用现有接口组织顺序脚本，不增加 TestCase 编排层。

编写前明确测试起点、操作步骤、预期和超时，并核对工具实际支持的能力。缺少接口时，先向用户说明定义、实现方式与修改范围，确认后再实现；按键、消息等待和断言方法尚未提供，不能当作已有 API 使用。

用户手动测试时，目标流程是 agent 配置钩子并启动游戏和后台采集程序，告知操作步骤后结束当前工作；用户完成后通知 agent，再读取报告分析。轮询由后台程序承担。目前独立后台采集流程尚未实现，需先补齐，不能将前台 wait 当作已支持的后台任务。

## 测试文件与清理

测试脚本放在 RM 工程根目录 test/，报告和截图放在 test/reports/ 下按本次运行区分的目录。区分临时测试与常用测试：

- 临时测试在运行结束、agent 读取报告并反馈结果后，及时清理本次脚本、报告和截图；用户手动测试期间保留到用户通知完成并分析结果。仅清理本次创建且已不再需要的文件。
- 常用测试脚本可以保留复用，提交仍需用户明确授权。
- 临时测试脚本、报告和截图禁止提交。提交前检查暂存区，确保没有混入这些文件。

当前不新增或修改 .gitignore；也不改变工程已有的忽略规则。临时测试的清理和提交检查独立执行，不依赖 ignore。

## 测试流程

1. 用 `session.launch(project, executable, port)` 上下文启动独立 NW.js 进程；启动时直接传入 `test` 参数，连接后等待引擎就绪并验证测试模式，不导航或刷新页面。Windows 传 nw.exe，macOS 传应用内 Contents/MacOS/nwjs。Windows/Linux 尚未实机验证。
2. 如需游戏命令，执行 `game.check_debug()`，然后 `commands()` 获取并缓存命令列表，`help(name)` 使用缓存。新增子插件命令或页面重载后用 `commands(refresh=True)` 刷新。没有列出的命令不猜测。
3. 用 `game.call(name, timeout=45, **args)` 调用；游戏端 Promise 完成才返回。当前内置 state/loadGame；loadGame 使用 Scene_Load 引擎流程，等待地图就绪，不等待地图剧情结束。
4. 截图使用 `game.screenshot(path)`。核对实际状态和画面；读档成功不等于剧情通过。默认不保存、不覆盖存档。
5. 测试完成或失败都退出上下文，关闭本次启动的进程组（macOS/Linux）或进程树（Windows Job Object，初始化失败时 taskkill /T 清理）；不能只断开调试连接。附加已有窗口用 `Game(port)`，close 只断开连接，不擅自关闭用户进程。

连接限本机。端口被占用、多游戏页面、缺少插件、命令异常均报告。调用超时抛出 `OperationTimeout`，携带 `operation_id`；用 `game.operation(id)` 重连查询 running/succeeded/failed/unknown，完成时包含 result 或 error。超时不撤销操作，不自动重发。unknown 表示页面已重载、结果已清理或请求未到达，不能当作未执行。游戏端失败也不保证引擎副作用已撤销。页面重载后重新检查能力。当前传输为单请求串行，不并发调用一个 Game。

## 扩展规则

Debug.js 是基础框架，通常不修改它。客户端按所需接口检查能力，工程已安装副本按实际接口更新。工程专用命令、金手指、控件和界面调整写在子插件中，加载顺序放在 Debug 之后。基础框架缺陷需要修复时单独说明并验证，不把项目逻辑混进去。

子插件用 `Debug.register(name, {description, parameters, handler})` 注册，agent 自动发现；目前参数校验支持整数及最小值。其他类型先扩展并测试基础校验，不能写未被校验器支持的声明。名称禁止重复。参考[子插件示例](examples/Debug_Project.js)。

HUD 可通过 `Debug.overlay` 访问，基础类通过 `Debug.classes` 访问。overlay 在 DOM 就绪后创建，子插件使用 DOMContentLoaded 或检查 readyState 后再扩展。不要使用 eval 执行命令行输入；界面控件与 agent 共用注册功能。

## 验证边界

已在 The Shadow 的 MZ/NW.js 上验证标准库 CDP、能力查询、存档 2 加载、截图、HUD 输入及关闭测试进程。指定事件测试已提供测试专用启动与执行接口；通用的新游戏、按键和传送命令仍未提供。当前 HUD 的 FPS 在引擎未启用计数器时显示 N/A。
