# macOS 当前构建状态

2026-10-16：Apple Silicon arm64，macOS 27.0.1，Python 3.11.15，Node 24.14.1。
已生成 `.app` 和 `.pkg`，14 组冻结自检通过，应用 ad-hoc 签名验证通过。PKG 未签名、未公证，安装位置为 `/Applications`。原生 UI、权限、实际安装卸载和干净机器验收未完成。Intel 与最低支持系统未验证。

本次环境的 hdiutil 无法使用磁盘管理服务，改用 `--format pkg`；默认 DMG 仍可在正常构建主机使用。图标通过 PNG-backed ICNS 封装，不依赖 iconutil。PKG 未发布，源码仓库保持 private。以下交接说明保留为复现与后续验收参考，历史“尚未执行”状态以本段为准。

构建命令可在下文示例末尾加 `--format pkg`。安装包包含项目对应源码、pyswisseph 源码和许可；源码目录不包含任何安装包。

---

# Mystery 0.11.1 macOS 打包交接

接收者使用交接包的 `repository/` 作为工程根目录。`release-assets/` 里的 setup.exe 供 Windows 功能核对，不能转换成 macOS 程序。Mac 必须从 Python、JavaScript 和离线资源重新构建。

## 当前状态

| 内容 | 状态 |
| --- | --- |
| 最新 Windows 0.11.1 安装包及对应源码 | 银灰磨砂界面重建版，哈希可核对 |
| 交接源码的平台入口 | 已选择 Cocoa、macOS 数据目录及 `runtime/node` |
| macOS 构建脚本、图标转换与 DMG 入口 | 已提供；尚未在 Mac 执行 |
| macOS GUI、WebGL、权限、签名及公证 | 需在目标 Mac 实测 |
| 项目许可证 | 以根目录实际 `LICENSE` 和 `OPEN_SOURCE_HANDOFF.md` 状态为准 |

版本号保持 0.11.1。Windows 已从交接源码重新构建；发布时保留随安装包生成的对应源码 ZIP。Mac 安装包需在目标系统构建。

## 准备环境

在 Apple Silicon 上构建 `arm64`，在 Intel 或完整 Intel 环境中构建 `x86_64`。Python、Node 和二进制依赖必须使用同一架构。先分别构建两种架构；不要合并两个 PyInstaller 可执行文件来冒充 universal2。[PyInstaller 架构说明](https://pyinstaller.org/en/stable/feature-notes.html#macos-multi-arch-support)

安装 Python 3.11 或 3.12、与架构一致的 Node.js（可优先与 Windows 参考包的 24.14.0 对齐），以及 Xcode Command Line Tools。最低支持 macOS 版本应由实际构建环境和测试结果确定，不能从源码声明推断。

```sh
xcode-select --install
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-macos.txt
.venv/bin/python scripts/check_desktop.py
.venv/bin/python run_desktop.py
```

pywebview 的 macOS 依赖由 pip 按平台解析，包括 PyObjC；不要安装记录了 pythonnet 等 Windows 组件的 `requirements-desktop-lock.txt`。[pywebview 安装说明](https://pywebview.flowrl.com/guide/installation.html)

首次安装依赖需要联网。若 pyswisseph 没有适配的 wheel，pip 会从源码编译，因此需要本机编译工具。不需要重跑地理索引生成、生图或 `vendor_iztro.py`，资源已随源码提供。项目许可证已确认为 AGPL-3.0-only，原文在根目录 `LICENSE`。

## 构建应用和 DMG

准备所用 Node 发行包自己的 `LICENSE` 和 Python 发行版的许可证文件。下面路径和 Bundle ID 必须替换为实际值；Bundle ID 应由发布者控制且升级时保持稳定。

```sh
.venv/bin/python scripts/build_macos.py \
  --node /absolute/path/to/node/bin/node \
  --node-license /absolute/path/to/node/LICENSE \
  --python-license /absolute/path/to/python/LICENSE \
  --bundle-id com.YOURDOMAIN.mystery \
  --swiss-source ../release-assets/pyswisseph-2.10.3.2.tar.gz
```

省略 `--swiss-source` 时，脚本会下载固定版本并验证固定 SHA-256。脚本将 Node、前端、iztro、tzdata、tzfpy、许可和源码收集到 `.app` 中；用系统工具将透明 PNG 转成 ICNS；检查代码签名并执行冻结后的算法自检；成功后生成 DMG。它不会读取 Windows 构建缓存。

产物位于 `output/macos/arm64/` 或 `output/macos/x86_64/`：`Mystery.app`、版本化 DMG、`build-manifest.json`、`requirements-macos-resolved.txt`。最后一项是该 Mac 实际解析的依赖版本记录。

同目录还保留 `sources/` 中的对应源码和上游源码，以及按架构命名的第三方许可 ZIP，供 `collect_release_assets.py` 汇总为 GitHub Release 附件。

省略 `--identity` 会生成 ad-hoc 开发签名。公开分发时，使用已配置的 Developer ID Application 证书，增加 `--identity "Developer ID Application: YOUR NAME (TEAMID)"` 并完成公证。脚本中的 JIT entitlement 用于内嵌 Node；实际签名与权限行为仍须检查。

## 原生验收

先在开发 Mac 上完成，再在没有 Python、Node 和项目目录的干净 Mac 上检查，确保实际使用的是内嵌资源。

- 从 DMG 拖入 Applications 后，以 Finder 双击启动；中文目录、空格路径、重启后启动均正常。
- 主星、三维星云、四类命盘、牌面、离线地球、五类问事及导航可用；重点检查 WKWebView 的 WebGL 2 和滚动、拖动、全屏行为。
- 十个算法自检全部成功，尤其确认紫微使用内嵌 Node，时区查询使用内嵌 tzfpy 数据。
- 创建、编辑、重启读取生日簿；检查星迹回放、导入导出、跨时区提醒。自检使用临时数据，不使用真实朋友资料。
- 验证文件夹选择、本地音乐、可播放网络直链，以及系统定位的同意、拒绝、超时和设置关闭。若 WKWebView 不提供定位，拒绝和回退应保持可用。
- AI 先使用离线模拟测试；如需真实服务，由测试者自行提供 Key，单独选择是否调用。
- 数据写入 `~/Library/Application Support/Mystery`，启动异常日志也在这里。删除应用后数据保留。

原生 UI 自检示例（先创建输出目录）：

```sh
mkdir -p .cache/mac-ui
output/macos/arm64/Mystery.app/Contents/MacOS/Mystery \
  --ui-test .cache/mac-ui/report.json --data-dir .cache/mac-ui/data
```

Intel 构建替换路径中的架构。必须打开 JSON 检查 `ok: true`；进程退出本身不代表 UI 验证通过。该检查只验证初始化，不能替代上面的交互验收。

## 公证和发布

使用自己的 Apple Developer 身份及 Keychain profile。不要将证书、密码、App 专用密码或 Keychain 数据放入仓库。

```sh
xcrun notarytool submit output/macos/arm64/Mystery-0.11.1-macos-arm64.dmg \
  --keychain-profile YOUR_PROFILE --wait
xcrun stapler staple output/macos/arm64/Mystery-0.11.1-macos-arm64.dmg
xcrun stapler validate output/macos/arm64/Mystery-0.11.1-macos-arm64.dmg
shasum -a 256 output/macos/arm64/Mystery-0.11.1-macos-arm64.dmg
```

仅在公证 Accepted、staple 和干净机器验收成功后，将发行说明标记为已签名并公证。公证附票会改变 DMG 字节；务必重新生成最终大小和 SHA-256，并更新构建清单，而不是沿用构建时的值。脚本默认记录 `notarized: false`、`ui_verified: false`，完成后由验收者依据记录更新。

以上是仓库 Release 的站外分发流程，不包含 Mac App Store 上架。[Apple 公证说明](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)
