> 历史交接记录。当前已在 Mac 构建 arm64 PKG，验收结果见 [验证记录](VALIDATION_0.11.1.md)。当前阶段只推源码并保持 private，安装包保留本地，不执行本文中的 Release 上传步骤。

# Mystery 0.11.1：Mac 接收与 GitHub 发布

这是当前完整交接包。Windows 安装包已从包含透明银灰磨砂界面、跨平台适配及中英 README 的源码重新构建。功能版本保持 0.11.1。

## 目录用途

| 路径 | 用途 |
| --- | --- |
| `repository/` | 直接作为 Git 仓库根目录：源码、离线资源、README 和产品图、LICENSE/COPYRIGHT、依赖、测试、构建脚本、GitHub 模板与发布文档 |
| `release-assets/` | 已重打的 Windows setup.exe、对应源码 ZIP、pyswisseph 源码、第三方许可 ZIP、构建清单和验证报告；上传到 GitHub Release |
| `HANDOFF_MANIFEST.json`、`SHA256SUMS.txt` | 交接文件的用途、大小与 SHA-256 |
| `先读交接说明.md` | 本说明的独立副本 |

**只把 `repository/` 内容提交 Git。** 安装包和源码压缩包放到 Release。不要在整个交接目录执行 `git add .`。

## 在 Mac 上按这个顺序做

1. 在解压后的交接目录运行 `shasum -a 256 -c SHA256SUMS.txt`，确认所有文件一致。
2. 进入 `repository/`，按 `docs/MACOS_BUILD.md` 安装 Mac 依赖、测试、打包目标架构、验收和完成所选签名分发流程。上游源码可直接使用 `../release-assets/pyswisseph-2.10.3.2.tar.gz`。
3. 按 `docs/GITHUB_PUBLISH.md`，以自己的 GitHub 账号创建仓库并推送。GitHub 登录、Git 身份和 Apple 签名凭据只留在 Mac，不在交接包中。
4. 使用 `scripts/collect_release_assets.py` 合并 Windows 附件和 Mac 构建产物，重新计算最终 SHA-256；按发布指南创建 Release 草稿、检查后发布。

项目自有代码与文档已由作者确认采用 **AGPL-3.0-only**；版权署名 **SaSa (SamanthaMengjunyu)**，详见 `repository/LICENSE` 和 `repository/COPYRIGHT`。第三方代码、数据和素材保留原许可及署名，见 `THIRD_PARTY_NOTICES.md`。安装包内附项目源码、固定版本 pyswisseph 源码和许可文件。

## 验证与平台边界

Windows 重建及实际检查范围见 `repository/docs/VALIDATION_0.11.1.md` 和 `release-assets/validation-windows.json`。新版安装包对应 `release-assets/Mystery-0.11.1-source.zip`，与本交接 `repository/` 逐文件核对。旧配色安装包不进入本交接包。

macOS 构建脚本与资源已准备，尚需在目标 Mac 完成 `.app`、DMG、原生交互、签名和公证等实测。不要将 Windows 验证记录当作 Mac 已通过的证据。

导出采用源码白名单并扫描已知 Key、私钥和私有路径类型，排除缓存、个人数据库、WebView 资料、音乐和凭据。Mac 打包产生的签名凭据、日志和私人测试数据也不要提交。
