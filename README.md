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

## MoviePilot v3

- v3 插件目录：`plugins.v3/apppushmsg`
- v3 市场清单：`package.v3.json`，要求 MoviePilot `>=3.0.0`。
- 插件市场地址与上文相同，v3 宿主读取对应版本的插件。
- 保存 token、API Key 并启用插件后生效；测试按钮使用已保存的配置。

### 消息类型选择

配置页根据宿主消息类型枚举动态生成多选项（当前 v3 使用 `MessageType`，也兼容早期 `NotificationType`）。

- 新配置默认全选，推送全部消息，包括未知或未指定类型的消息。
- 选择部分类型时，只接收所选类型；优先读取 `type`，缺失时读取 `mtype`。
- 清空选择后停止自动推送，手动测试仍可使用。
- 已指定专用通知渠道的消息继续由该渠道处理。
- 保留 `message_types` 配置键及中文值，兼容旧版选择、枚举名称和枚举对象。
- 全选保存的是当前类型列表；宿主未来新增类型后，如需接收，请重新全选并保存。

本地验证（无需 MoviePilot 或真实推送凭据）：

```bash
python3 -m unittest discover -s tests -v
```
