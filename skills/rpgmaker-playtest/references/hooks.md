# 运行时钩子

Agent 使用 Python `Hook` 和 `Hooks`，筛选字段直接作为关键字传入。内部负责生成传给 Debug 的配置，独立于 command 注册。

```python
from hooks import Hook, Hooks
from event_test import launch_event_test

hooks = Hooks()
hooks.add(Hook('started', on='process.start'))
hooks.add(Hook('ready', on='game.ready'))
hooks.add(Hook('error', on='runtime.error'))
hooks.add(Hook('fatalError', on='runtime.error', fatal=True, action='finish'))
hooks.add(Hook('warning', on='runtime.warning'))
hooks.add(Hook('exit', on='process.exit'))
hooks.add(Hook('calls', on='event.call'))
hooks.add(Hook('door', on='switch.change', id=21, value=True, action='finish'))

with launch_event_test(project, nwjs, common_event_id=138,
                       hooks=hooks, report_dir=report_path) as game:
    result = game.wait(timeout=30)
    while result['status'] == 'running':
        result = game.wait(timeout=30)
```

运行中使用 `game.add_hook(Hook(...))`、`game.list_hooks()`、`game.remove_hook(name)`、`game.clear_hooks()`。启动前的管理对象也有 `add/remove/clear`。同一会话名称唯一；不支持的信号、筛选字段或 action 注册时报错。

## 信号

| on | 时机 | 筛选字段 |
| --- | --- | --- |
| process.start | Python 创建 NW.js 后 | pid |
| game.ready | 正常启动为标题场景开始后，事件测试为地图场景开始后，一次会话仅一次 | 无 |
| startup.failed | 启动抛出异常或超时 | message |
| runtime.error | window.error、unhandledrejection、SceneManager.catchException、console.error；引擎错误处理调用 stop 时 fatal=true | origin、fatal |
| runtime.warning | console.warn | origin |
| process.exit | Python 确认本次进程退出 | code、requested |
| event.start | Game_Interpreter.setup 返回后 | mapId、eventId、commonEventId、executionId、parentId |
| event.call | 原版 command117 调用有效公共事件前 | 同上；commonEventId 是调用目标 |
| event.command | executeCommand 前，以及返回成功后 | 同上及 index、sourceIndex、code、phase |
| event.end | terminate 返回后，仅原来有执行列表时 | 与 event.start 相同 |
| variable.change | Game_Variables.setValue 后实际值改变 | id、value |
| switch.change | Game_Switches.setValue 后实际值改变 | id、value |

`phase` 为 before/after；after 表示解释器接受指令，不表示动画结束。阻塞指令可能多次产生 before。index 为解释器当前列表下标；本次测试根列表额外给出源列表 sourceIndex。执行编号区分每次 setup，setupChild 记录父执行编号。

变量与开关记录 oldValue/newValue；value 是筛选新值的别名。逐次捕获 setValue，不监听直接修改 _data。注册只观察后续变化。值以 JSON 快照记录，不可序列化值退为字符串。事件调用仅识别原版 command117；插件其他调用可产生 event.start，但不猜测公共事件身份。

## 动作和报告

- record：记录并继续。
- finish：记录并提出结束请求；Python 收到后写报告、解除钩子并关闭本次进程。
- once 默认 False；True 时首次命中后停用，列表中保留 inactive 状态，便于查询。

方法包装按采集类别共享。移除或停用最后一个相关钩子时恢复方法并移除监听。clear 解除全部采集。不同错误入口可能记录同一次异常的不同传播阶段。

Debug 通过 Runtime.addBinding / Runtime.bindingCalled 推送记录，连接前暂存内存，连接后按顺序发送。Python 的 `game.poll()` 接收已送达的 CDP 事件，`wait` 等待 socket 可读；不再反复执行 JavaScript 查询日志。后台脚本持续接收并写入 events.jsonl 和 session.json，agent 无需等待。启动期间由启动器接收。启动钩子提前结束时返回已结束的 game，不能继续添加钩子或截图。

进程启动与退出记录始终保留用于诊断；匹配到的钩子 ID 同时记录。状态为 running/finished/failed/exited/cancelled。非工具主动退出不自动称为崩溃，结合退出码、runtime.log 和错误记录判断。硬崩溃前尚未传出的内存记录可能丢失。

不传 hooks 时，事件测试默认提供根事件结束 finish 和普通错误 record 和 fatal=true 错误 finish 钩子；显式传 Hooks 时完全使用传入的配置。只有 record 的会话不会因事件结束自动关闭。

工程外临时配置通过环境变量路径传入；游戏仍以 test 启动。存档目录重定向和原版事件测试启动属于会话设置，不受 clear_hooks 影响；随进程和临时目录清理。工程文件不修改，指定报告保留。

## 验证状态

2026-10-16 已执行脚本测试与真实 MZ/NW.js 验收，具体范围和未覆盖场景见[功能清单](capabilities.md)。

错误策略：普通 console.error、window.error、unhandledrejection 只记录（fatal=false）。SceneManager.catchException/onError 处理过程中实际调用 stop 后另发 fatal=true，默认仅此类错误结束游戏。单独 stop 不算错误。原版 onReject 转交 onError，因此未处理的 Promise 若引擎因此停止，同样属于 fatal。插件打印可恢复错误不会触发关闭。
