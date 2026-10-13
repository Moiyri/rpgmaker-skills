# RM 项目目录架构

以 RM 工程根目录作为 Git 仓库根目录。下方列出可能用到的目录，按实际需求使用；不要求一次创建全部目录。地图、数据库与初始化的组织见[项目架构](project-architecture.md)，素材命名统一见[命名规则](naming-rules.md)。

## 目录树

```text
工程根目录/
├── data/                       RM 数据库、地图与系统数据
│   └── configs/                可选：复杂功能的外置配置
├── js/
│   ├── libs/                   引擎与运行依赖库
│   ├── plugins/                RM 插件及通过插件流程加载的库
│   │   └── tools/              工具库，例如 gsap.min.js
│   └── plugins.js              插件注册、启用、顺序和参数
├── img/
│   ├── characters/             角色、NPC、物件行走图
│   │   ├── heroes/             可选：主要角色行走图
│   │   ├── objects/            可选：物件行走图
│   │   └── animations/         可选：多帧图像动画
│   ├── pictures/               遮罩、叠加图、立绘、事件图片及未分类杂项
│   ├── ui/                     没有现有对应目录的界面图片
│   │   ├── diaries/            可选：日记界面图片
│   │   └── galleries/          可选：画廊界面图片
│   ├── character_standings/    可选：独立立绘目录
│   ├── cgs/                    可选：独立 CG 目录
│   ├── maps/                   可选：地图叠加图层
│   ├── parallaxes/             地图远景、编辑器预览图
│   ├── tilesets/               图块素材
│   ├── system/                 窗口皮肤、图标及插件指定系统图片
│   ├── titles1/                标题主图
│   ├── titles2/                标题叠加图
│   ├── faces/                  头像
│   ├── enemies/                前视敌人图片
│   ├── sv_enemies/             侧视敌人图片
│   ├── sv_actors/              侧视角色战斗图
│   ├── battlebacks1/           战斗背景下层
│   └── battlebacks2/           战斗背景上层
├── audio/
│   ├── bgm/                    背景音乐
│   ├── bgs/                    环境音、背景音效
│   ├── me/                     音乐效果，如胜利提示
│   ├── se/                     音效，包括脚步声
│   └── vsc/                    可选：MUSH 角色配音
│       ├── chap01/             按章节分类的示例
│       └── veloria/            按角色分类的示例
├── movies/                     视频
├── fonts/                      字体
├── effects/                    MZ 特效及其依赖资源
│   ├── Model/                  特效使用的模型资源
│   └── Texture/                特效使用的纹理资源
├── docs/                       可选：项目设计与制作文档
├── tools/                      可选：工程外运行的辅助脚本
├── save/                       运行生成：存档，具体位置以发行平台为准
├── AGENTS.md                   项目专用 agent 约定
└── .gitignore                  Git 忽略规则，具体内容后续约定
```

## 放置原则

- **行走图**放在 `img/characters/`。使用 heroes、objects、animations 等子目录前，先确认编辑器与相关插件的路径支持；素材包含多帧并不意味着必须搬到 animations。
- **pictures 的用途**：`img/pictures/` 放遮罩、叠加图、立绘，以及在游戏中通过事件调用的图片，例如章节 banner；也放无法归入其他大类的杂项图片。LL_StandingPicture 默认读取这里。不能仅因为某素材通过显示图片呈现，就把已有明确分类的素材全部放入 pictures。
- **已有明确分类的图片**按用途归档，例如 CG 放在 `img/cgs/`、地图图层放在 `img/maps/`，无现有对应目录的界面图片放在 `img/ui/`。使用独立目录时核对加载方式与引用。立绘默认放 pictures；character_standings 仅在工程明确采用并支持独立立绘目录时使用。
- **地图图层**放在 `img/maps/`，由所用图层插件或项目配置读取；**远景和编辑器预览图**放在 `img/parallaxes/`。远景也可以参与游戏渲染，不限定为仅供预览。
- **UI 图片优先复用对应目录**：修改菜单、标题等已有界面时，资源放入引擎或目标工程已有的对应资源目录，不因为修改界面就另建 ui 分类。标题图片沿用 `img/titles1/`、`img/titles2/`，窗口与图标沿用 `img/system/`；菜单资源先核对实际工程及插件的目录，不假定原生 RM 必定存在 `img/menus/`。
- **没有对应目录的界面**，例如日记、画廊，其专用图片放在 `img/ui/`；按需要设 diaries、galleries 等子目录。游戏插件按实际路径读取，使用现成插件时先确认加载支持。
- **音频**按 BGM、BGS、ME、SE 分类。MUSH 配音使用 `audio/vsc/`；章节和角色子目录是分类选项，不要求同时套两层，具体规则见命名文档。
- **视频、字体、特效**分别放在 movies、fonts、effects。保留引擎和工具要求的目录大小写及相对路径；特效依赖资源应随主文件一同检查。
- **库与工具**：GSAP 放在 `js/plugins/tools/`，按插件加载顺序接入；根目录 `tools/` 存放在游戏外执行的辅助脚本，两者用途不同。
- **外置配置**仅在复杂需求确有需要时使用 `data/` 下的专用目录；树中的 configs 是候选目录名。大部分插件功能仍使用 RM 参数管理器。

目录树不意味着自动搬移既有素材。实施前检查目标插件的读取路径和资源引用；目录大小写必须一致。原始素材、临时文件、测试输出的存放方式，Git、docs 与 AGENTS.md 的维护规则见[项目管理](project-management.md)。
