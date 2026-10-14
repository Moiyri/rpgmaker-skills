# 运行时钩子

Agent 使用 Python `Hook` 和 `Hooks`，筛选字段直接作为关键字传入。内部负责生成传给 Debug 的配置，独立于 command 注册。

```python
from hooks import Hook, Hooks
from event_test import launch_event_test

hooks = Hooks()
hooks.add(Hook('started', on='process.start'))
hooks.add(Hook('ready', on='game.ready'))
hooks.add(Hook('error', on='runtime.error', action='finish'))
hooks.add(Hook('warning', on='runtime.warning'))
hooks.add(Hook('exit', on='process.exit'))
hooks.add(Hook('calls', on='event.call'))
hooks.add(Hook('door', on='switch.change', id=21, value=True, action='finish'))

with launch_event_test(project, nwjs, common_event_id=138,
                       hooks=hooks, report_dir=report_path) as test:
    result = test.wait(timeout=30)
    while result['status'] == 'running':
        result = test.wait(timeout=30)
```

运行中使用 `test.add_hook(Hook(...))`、`test.list_hooks()`、`test.remove_hook(name)`、`test.clear_hooks()`。启动前的管理对象也有 `add/remove/clear`。同一会话名称唯一；不支持的信号、筛选字段或 action 注册时报错。

## 信号

| on | 时机 | 筛选字段 |
| --- | --- | --- |
| process.start | Python 创建 NW.js 后 | pid |
| game.ready | 第一次 Scene_Map.start 返回后，一次会话仅一次 | 无 |
| startup.failed | 启动抛出异常或超时 | message |
| runtime.error | window.error、unhandledrejection、SceneManager.catchException、console.error | origin |
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

`test.poll()` 增量采集至 events.jsonl，并返回 session.json 状态；`wait` 分段轮询。Python 持续调用这些方法才能持续保存游戏记录。启动期间由启动器负责轮询。启动钩子提前结束时返回已结束的 test，不能继续添加钩子或截图。

进程启动与退出记录始终保留用于诊断；匹配到的钩子 ID 同时记录。状态为 running/completed/failed/exited/cancelled。非工具主动退出不自动称为崩溃，结合退出码、runtime.log 和错误记录判断。硬崩溃前尚未传出的内存记录可能丢失。

不传 hooks 时，事件测试默认提供根事件结束 finish 和运行错误 finish 两个钩子；显式传 Hooks 时完全使用传入的配置。只有 record 的会话不会因事件结束自动关闭。

工程外临时配置通过环境变量路径传入；游戏仍以 test 启动。存档目录重定向和原版事件测试启动属于会话设置，不受 clear_hooks 影响；随进程和临时目录清理。工程文件不修改，指定报告保留。

## 验证状态

已编写实现与 Python 行为用例。本轮按用户要求未执行测试、语法检查或引擎验收。12 个信号、父子解释器追踪、恢复包装、报告后退出均待运行验证。
