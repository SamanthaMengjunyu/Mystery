# 数据与隐私

Mystery 没有账号系统。排盘、抽牌、地图搜索、生日簿和本地音乐在本机处理。

## 保存位置

| 平台 | 默认目录 |
| --- | --- |
| Windows | `%LOCALAPPDATA%\Mystery` |
| macOS | `~/Library/Application Support/Mystery` |
| 其他平台的源码运行 | `$XDG_DATA_HOME/Mystery`，默认 `~/.local/share/Mystery` |

`--data-dir` 可覆盖目录。`records.sqlite3` 保存生日簿与星迹，`preferences.json` 保存偏好，`music.json` 保存选择的音乐目录与播放选项，`webview-profile` 用于 WebView 临时资料。启动失败时会生成 `startup-error.log`。导出文件可能包含个人资料，公开问题报告前需自行脱敏。

## 可选网络功能

- AI：用户主动读取模型、请求解读或追问时，程序连接其配置的 API 地址；相应问题、排盘和对话数据发送至该服务。服务的数据政策由其提供者决定。API Key 不写入应用偏好；示例脚本可从环境变量读取 Key。
- 定位：取得同意后向系统申请大致位置；系统定位服务可能联网。坐标仅暂存内存十分钟，不写入生日簿、星迹或 AI 请求。拒绝后可继续使用设备时区。
- 网络音频：主动播放 HTTP/HTTPS 直链时连接目标服务。选择本地文件夹仅向本机播放器提供音频。

项目未实现后台账号同步或云端资料库。卸载 Windows 应用会保留本地数据；需要清除时先关闭应用，再删除对应数据目录。macOS 的运行和权限行为需按打包交接清单实测。
