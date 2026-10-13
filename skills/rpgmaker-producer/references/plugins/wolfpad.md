# WolfPad：手柄支持

用户指定的手柄支持候选。准确文件名为 `WolfPadMVZ.js`，不是 WolfPadMZ.js。shadow 注册名 `WolfPadMVZ`，已启用。

作者 Lone Wolf（基于 Yoji Ojima 的函数），本地帮助版本 2/20/2024c。[原发布页](https://forums.rpgmakerweb.com/index.php?threads/gamepad-extender-mvz.127243/)来自源码，当前网页可访问性未验证。

扩展标准按键、摇杆、多手柄和震动。MZ 提供 `vibrate`、`clearVibration` 命令；脚本入口包括 `WolfPad.isPressed/isTriggered/isRepeated/isLongPressed`、`lstick8/rstick8`。大部分扩展需要脚本对接，不等于安装后自动完成游戏全部手柄交互。调用前核对按键名和手柄索引。

声明支持有限的 MV 向后兼容，插件命令仅 MZ。实际控制器支持取决于浏览器/NW.js；帮助说明部分手柄震动需要 Steam Input，Steam Input 断连后的重连可能需重启。没有实际设备测试前不声称所有手柄适配。

源码有独立再分发和商业使用说明，本库只记录资料，不复制插件。验证实际目标手柄的按键、摇杆、菜单操作和震动，区分脚本调用成功与设备真实反馈。本次仅核对本地帮助与注册状态。
