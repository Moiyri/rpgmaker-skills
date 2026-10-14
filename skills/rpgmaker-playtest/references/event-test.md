# 事件测试

## 定义

从工程已保存的地图事件或公共事件读取指令，交给引擎原版事件测试执行。地图编号仅定位源文件。运行环境由 `DataManager.setupEventTest()` 创建：空白地图、初始队伍、玩家坐标 (8, 6)。`Game_Map.setupTestEvent()` 使用事件 ID 0 执行，因此没有源地图事件的“本事件”上下文。

## 调用

```python
from event_test import launch_event_test

with launch_event_test(project, nwjs, common_event_id=138,
                       commands=(5, 12), report_dir=report_path) as test:
    result = test.wait(timeout=30)
    while result['status'] in ('pending', 'running'):
        result = test.wait(timeout=30)
```

地图事件改用 `map_id=31, event_id=3, page=1`。页码从 1 开始。`commands=(start,end)` 使用源列表原始下标，从 0 开始，包含 start、不包含 end；省略时传入整个列表。所选记录原样保留，包括缩进，不补写结束指令。引擎在列表耗尽时结束执行。

`prepare_event_test` 接受相同的目标和选区参数，只读并返回计划；启动前核对源文件指纹。公共事件不需要地图。`timeout` 是启动等待时间，`test.wait(timeout=30)` 是一次分段等待时长。

## 启动实现

NW.js 继续传入 `test`。Debug 仅在存在本次临时配置时包装 `Scene_Boot.startNormalGame`，依次执行：

```js
window.$testEvent = config.commands;
DataManager.setupEventTest();
SceneManager.goto(Scene_Map);
```

原版地图加载与 `setupTestEvent` 接管后续执行，Debug 的观察统一由 [Hook 对象接口](hooks.md) 提供。没有额外的事件调度或并行事件隔离。

这复用了原版执行流程，但没有使用 `etest` 的文件入口：数据库读取工程已保存的普通 JSON，选中指令通过工程外的临时配置传入。工程数据库、引擎源码、编辑器生成的 `Test_*.json` 均不修改。

## 报告与清理

`session.json` 记录源目标、状态与错误；`events.jsonl` 记录所配置钩子的命中信息及进程生命周期；`runtime.log` 保存进程输出。报告供 agent 分析，用户操作对白和选项。

调用 `poll()` 或 `wait()` 收到 finish 请求后，先写报告，再关闭本次进程。调用方持续分段等待以收集日志。退出上下文清理进程和临时配置、测试存档；报告保留。监听包装在停止时解除，退出进程后全部释放。完成表示指令执行结束，功能是否符合预期需按测试目标判断。

## CLI

```sh
python3 scripts/event_test.py PROJECT --common-event-id 138 --start 5 --end 12
python3 scripts/event_test.py PROJECT --map-id 31 --event-id 3 --run --executable NWJS --report-dir REPORT_DIR
```

默认只展示读取结果，`--run` 才启动游戏。

## 验证状态

本轮按用户要求未运行测试或启动游戏。此前自定义地图测试的验证结果不适用于重构后的流程。

编辑器对分支内选区、缩进和续行的导出处理尚待样例核对。当前按原始记录传递，不将其宣称为已完全复现编辑器的选区生成规则；遇到这类测试目标先反馈并核对样例。
