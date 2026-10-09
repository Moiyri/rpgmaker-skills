---
name: rpgmaker-playtest
description: 启动或附加 RPG Maker MZ 的 NW.js 游戏，动态查询测试命令、准备测试现场、读档并截图验证。需要游戏内实际测试、复现问题或编写工程专用金手指时使用；内置可选 Debug.js，Python 连接仅使用标准库。
---

# RPG Maker Playtest

使用 Python 3.10+ 标准库客户端，不安装 Playwright 或浏览器。先读取工程约定，确认工程、NW.js 可执行文件与测试目标。实际接口见 scripts/playtest.py、scripts/session.py；[最小测试](examples/load_game.py)。

## 选择是否安装 Debug

- 只连接、截图或观察已有页面不需要 Debug。
- 需要动态命令、读档、HUD 或金手指时先检查工程是否已有兼容 Debug。按用户需求安装，不因测试就自动修改插件配置。
- 用户要求这些能力且工程尚无实现时，可安装随附 assets/Debug.js 到 js/plugins/playtest/Debug.js；同名现有文件先核对，不覆盖用户定制。
- 安装、启用、排序、卸载清单均使用[插件技能](../rpgmaker-plugins/SKILL.md)的正式脚本。移除注册与删除源码是两件事。
- Debug 仅在 `?test` 模式启用。普通启动不公开接口、不创建 HUD。反引号显隐、`/` 输入、Escape 退出；命令行目前只回显，不执行命令。

## 测试流程

1. 用 `session.launch(project, executable, port)` 上下文启动独立 NW.js 进程；自动添加测试参数。Windows 传 nw.exe，macOS 传应用内 Contents/MacOS/nwjs。Windows/Linux 尚未实机验证。
2. 如需游戏命令，执行 `game.check_debug()`，然后 `commands()` 获取命令列表，`help(name)` 获取参数。没有列出的命令不猜测。
3. 用 `game.call(name, **args)` 调用；游戏端 Promise 完成才返回。当前内置 state/loadGame；loadGame 使用 Scene_Load 引擎流程，等待地图就绪，不等待地图剧情结束。
4. 截图使用 `game.screenshot(path)`。核对实际状态和画面；读档成功不等于剧情通过。默认不保存、不覆盖存档。
5. 测试完成或失败都退出上下文，关闭本次启动的进程；不能只断开调试连接。附加已有窗口用 `Game(port)`，close 只断开连接，不擅自关闭用户进程。

连接限本机。端口被占用、多游戏页面、缺少插件、命令异常或超时均停止并报告。超时不代表操作被撤销，不自动重发读档等操作。页面重载后重新检查能力。当前传输为单请求串行，不并发调用一个 Game。

## 扩展规则

Debug.js 是基础框架，通常不修改它。工程专用命令、金手指、控件和界面调整写在子插件中，加载顺序放在 Debug 之后。基础框架缺陷需要修复时单独说明并验证，不把项目逻辑混进去。

子插件用 `Debug.register(name, {description, parameters, handler})` 注册，agent 自动发现；目前参数校验支持整数及最小值。其他类型先扩展并测试基础校验，不能写未被校验器支持的声明。名称禁止重复。参考[子插件示例](examples/Debug_Project.js)。

HUD 可通过 `Debug.overlay` 访问，基础类通过 `Debug.classes` 访问。overlay 在 DOM 就绪后创建，子插件使用 DOMContentLoaded 或检查 readyState 后再扩展。不要使用 eval 执行命令行输入；界面控件与 agent 共用注册功能。

## 验证边界

已在 The Shadow 的 MZ/NW.js 上验证标准库 CDP、能力查询、存档 2 加载、截图、HUD 输入及关闭测试进程。不是完整自动化框架：未提供新游戏、按键或传送的高层命令。当前 HUD 的 FPS 在引擎未启用计数器时显示 N/A。
