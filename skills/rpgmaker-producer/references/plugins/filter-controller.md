# FilterControllerMZ：滤镜

用户评价：非常好用。滤镜需求优先使用它，不自行重写滤镜系统；先核对现有效果能否满足，确有缺口再与用户讨论。

- JS：`FilterControllerMZ.js`；shadow 注册路径：`visual/FilterControllerMZ`，已启用。
- 作者 Tsukimi；本地版本 1.1.0，MZ。
- [作者源码](https://raw.githubusercontent.com/cji3bp62000/RPGMaker-plugins/master/plugin-list/FilterControllerMZ/FilterControllerMZ.js)。已读取在线源码确认来源；不要混用 MV 版 FilterController。

提供 blur、glow、godray、noise、oldfilm、crt、glitch、shockwave、displacement 等滤镜，可作用于画面、地图、角色、图片等目标。通过 `createFilter` 创建，`setFilter` 设置，`moveFilter`/`moveFilterQ` 做过渡，`eraseFilter` 删除；使用唯一 filterId 管理生命周期。参数顺序随滤镜类型变化，使用前查询源码/帮助，不猜数值含义。

目标标识包含原版拼写 `SepcificChar`、`ExcludeSepcificChar`，不要擅自纠正成另一种拼写。支持地图/事件备注自动创建滤镜；帮助说明这类滤镜离开地图时删除，不把这一行为套用于所有命令创建的滤镜。

本地文件内含 pixi-filters 代码，不默认要求另外下载同名滤镜库。displacement 素材放 `img/pictures/`，声明要求尺寸为 2 的幂，如 512×512；先检查素材，告知用户处理规格。参数 `decimalVariable` 会影响游戏变量的小数行为，启用前核对。

验证滤镜目标、过渡、取消、转场和性能；本次仅阅读声明与源码，未运行验证。不复制第三方源码入技能库。
