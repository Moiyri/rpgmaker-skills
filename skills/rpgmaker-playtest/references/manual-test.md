# 用户手动测试

执行脚本放在工程 test/，正常游玩或读档参考 examples/manual_game.py，指定事件参考 examples/manual_event.py，填写实际技能路径、NW.js 路径和事件目标。使用 Hook/Hooks；普通错误设 record，fatal=True 的错误设 finish，其他终止条件按测试目标配置。普通 event.end 可只记录，让用户观察结束画面后自行关闭。

## 启动

```sh
python3 SKILL/scripts/manual_test.py start PROJECT PROJECT/test/manual_event.py
```

start_manual 创建 test/reports/脚本名-时间-随机后缀/，分离启动执行脚本。脚本通过 collect_manual 进入已有会话上下文。启动端只等待 collector.json 的启动确认，返回报告位置后 agent 告知操作步骤并结束当前工作。starting 或 startup_wait_expired 不代表游戏已就绪；失败检查 collector.log 与 session.json，不重复拉起游戏。

## 采集实现

Debug 钩子将记录通过专用 CDP binding 发送到 Python。连接前记录暂存在游戏内存，绑定完成后顺序发送。Python 持续读取 WebSocket 的 Runtime.bindingCalled，追加写报告；不通过游戏 fs 写报告，也不轮询 Debug 日志。stdout/stderr 写入 runtime.log，进程句柄用于确认退出。

finish 命中后先保存记录，再关闭本次游戏。用户关闭游戏时记录退出码；采集脚本退出上下文完成清理后，collector 状态变为 finished。硬崩溃可能丢失尚未送达的记录；采集进程强制终止不保证清理成功。

## 读取

用户通知测试完成后：

```sh
python3 SKILL/scripts/manual_test.py report REPORT_DIRECTORY
```

此命令只读文件，不连接游戏。collector.json 表示后台脚本状态，session.json 表示游戏会话状态；collector 的 finished 不代表功能通过。events.jsonl 每条带 seq、time、signal、hooks 及信号数据。session.json 包含结束原因、触发钩子、持续时间、错误和警告计数、进程退出信息。先读摘要，再按具体目标查看证据。

launch.json 保存采集进程 PID、脚本和工程路径；collector.log 保存脚本输出与异常。报告由 agent 阅读。分析并反馈后清理本次临时脚本和报告；常用脚本保留。临时文件禁止提交，暂不改 .gitignore。

两个启动函数都返回 Game。launch 保留正常标题流程，之后可用 game.call("loadGame", slot=2) 读档；launch_event_test 准备原版事件测试。两者共用钩子、CDP 采集、报告和进程清理。game.wait() 默认等待到结束，timeout 参数用于分段等待。后台 collect_manual 使用同一个 Game API。普通启动沿用工程存档路径以支持读档；事件测试继续使用临时存档目录。2026-10-16 已在合成 MZ 工程验收，具体范围见[功能清单](capabilities.md)。
