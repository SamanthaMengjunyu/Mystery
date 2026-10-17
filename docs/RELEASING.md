# 构建与发布 0.11.1

## 从 Mac 发布到 GitHub

交接包中 `repository/` 是仓库根目录，`release-assets/` 是最新 Windows 发行附件。完整步骤见 [GITHUB_PUBLISH.md](GITHUB_PUBLISH.md)，Mac 打包见 [MACOS_BUILD.md](MACOS_BUILD.md)。二进制和源码压缩包放到 GitHub Release，源码和必要离线资源提交 Git。

项目自有代码和文档采用 AGPL-3.0-only，署名 SaSa (SamanthaMengjunyu)。保留根目录 `LICENSE`、`COPYRIGHT`、第三方声明、全部资源来源与许可。

## Windows 重新构建

在 Windows x64 上准备 Python 3.12、Node.js、Inno Setup 6/7 和 WebView2：

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-desktop-lock.txt
.venv/Scripts/python scripts/check_desktop.py
.venv/Scripts/python scripts/build_desktop.py
```

在隔离数据目录运行冻结后的 `Mystery-0.11.1.exe --self-test ... --data-dir ...`；检查 JSON 的每项 `ok: true`。实际界面验收可用 `--ui-test`（会短暂打开原生窗口），并检查原生交互。版本号相同不代表文件相同，重建后以 SHA-256 为准。

完成全部源码和文档修改后，再依次执行：

```powershell
.venv/Scripts/python scripts/package_release.py --source-only
.venv/Scripts/python scripts/build_installer.py
.venv/Scripts/python scripts/check_installer.py --work-dir .cache/installer-verification-new
```

`--source-only` 准备使用说明、许可、pyswisseph 源码和当前对应源码，不声称执行验证。`check_installer.py` 在独立目录和独立卸载注册项中静默安装、重装、卸载并检查数据保留；该目录必须是尚未使用的 `.cache` 子目录。

旧的无参数 `package_release.py` 会读取历史本地 UI 验证文件，不用于当前重建证据。当前验证报告应绑定新版 EXE、setup.exe 和源码 ZIP 的哈希。完成安装后不要再修改对应源码；如有修改，需重新生成源码 ZIP 和安装包。

## 交接包导出

原始 Windows 工程中执行 `python scripts/prepare_opensource.py --output output/NEW-HANDOFF --zip`。脚本核对安装包、EXE、上游源码、当前源码 ZIP 的一致性和验证报告，导出干净仓库、Release 附件及哈希清单。不会覆盖已有交接目录。

导出依赖本机 `output/release`，Mac 接收者不需要重新运行这个导出脚本。Mac 使用 `collect_release_assets.py` 把已有 Windows 附件与最终 Mac DMG 合并。公证、附票或重新压缩会改变字节，务必在这些操作后重新生成 SHA-256 清单。
