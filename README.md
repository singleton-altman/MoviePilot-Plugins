# MoviePilot-Plugins

`APPLitePush` 单插件仓库。

## 仓库地址

- `https://github.com/singleton-altman/MoviePilot-Plugins`

## 插件市场配置

在 MoviePilot 的环境变量中配置：

```bash
PLUGIN_MARKET=https://github.com/singleton-altman/MoviePilot-Plugins
```

如果已经配置了其它插件市场，使用英文逗号追加：

```bash
PLUGIN_MARKET=https://github.com/jxxghp/MoviePilot-Plugins,https://github.com/singleton-altman/MoviePilot-Plugins
```

## 当前插件

- `APPLitePush`
  - 插件目录：`plugins/apppushmsg`
  - 功能：保存本地 token，支持测试推送，并根据 MoviePilot 消息内容转发到 APPLitePush 接口
