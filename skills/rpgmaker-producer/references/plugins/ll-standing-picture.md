# LL_StandingPicture：常用立绘

用户经验：最常用的立绘插件，能满足大部分立绘需求。普通对话立绘优先检查它，不默认开发新立绘系统；超出能力的复杂需求另行讨论。

准确文件名 `LL_StandingPicture.js`，shadow 注册路径 `ui/LL_StandingPicture`。作者 Lulu's Church，本地文件头版本 2.6.3，面向 MZ。[官方说明](https://nine-yusha.com/plugin-spicture/)来自 @url。

参数 `sPictures` 配置立绘 ID、图片、各位置坐标、缩放、透明度等；图片位于 `img/pictures/`。先检查用户素材，再告诉用户统一尺寸、透明背景和命名等所需处理，不能假定素材已经符合布局。

通过消息控制符显示最多 4 个立绘：`\F[id]`、`\FF[id]`、`\FFF[id]`、`\FFFF[id]`；用 `\M[yes]` 等动作控制符表演，`\AA[F]` 聚焦并暗化其他角色。`\FH[ON]` 保持显示，`\FH[OFF]` 取消保持并随窗口关闭消除。命令 `processChar` 可在消息窗口外执行控制符；另有 `setEnabled`、`setTone`。

立绘切换支持淡入或各方向进入；动作是现成图片的演出，不等同骨骼动画或素材自动生成。与消息插件合用时验证控制符、层级、关闭消息和跨场景表现。当前仅核对本地声明，未做运行验证。
