# 在 Mac 上推送 Mystery 并发布安装包

以下为维护者在 Mac 上复现建仓和后续发布的流程。当前阶段只推送源码，仓库保持 private，安装包保留本地。示例仓库名为 `Mystery`，如改名，替换所有 `SamanthaMengjunyu/Mystery`。不要上传整个交接 ZIP 作为代码仓库。

## 1. 校验与构建 Mac 安装包

解压后，先在交接目录执行：

```sh
shasum -a 256 -c SHA256SUMS.txt
cd repository
```

按 [MACOS_BUILD.md](MACOS_BUILD.md) 构建和验收 Mac 安装包。所需源文件、资源、许可、Windows 新安装包及对应源码均已在交接包中，无需再从原 Windows 工程取文件。Mac 的 Python/Node、Xcode 工具、GitHub CLI 和个人签名凭据由本机准备。

## 2. 推送源码

安装 Git 与 [GitHub CLI](https://cli.github.com/)，然后登录自己的账号：

```sh
gh auth login
gh auth setup-git
gh auth status
git init -b main
git var GIT_AUTHOR_IDENT
```

如最后一条提示未配置身份，在当前目录设置 `git config user.name "SaSa"`，并将 `git config user.email` 设置为你在 GitHub Settings → Emails 中实际显示的邮箱或隐私 no-reply 地址。不要使用示例邮箱。

确认 `git status --short` 中只有源码、文档、截图和许可文件，然后执行：

```sh
git add .
git diff --cached --stat
git commit -m "Release Mystery 0.11.1"
gh repo create SamanthaMengjunyu/Mystery --private --source=. --remote=origin --push
```

此命令会创建 private 仓库并推送；检查完成且作者明确确认后才可改为 public。如果仓库已存在，使用下面两条替代 `gh repo create`；目标仓库需为空，不要在 GitHub 端预先添加 README 或 LICENSE：

```sh
git remote add origin https://github.com/SamanthaMengjunyu/Mystery.git
git push -u origin main
```

如果目标仓库已有提交，先克隆到另一个目录并复制 `repository/` 内容再提交；不要强推覆盖已有历史。

项目简介可填：`星云里的排盘、抽牌、生日簿与专注音乐。Local-first charts, cards, birthdays & music.`。建议 Topics：`desktop-app`、`threejs`、`pywebview`、`astrology`、`tarot`、`local-first`。README 已含中英文介绍、作者主页、产品图和许可证。

## 3. 汇总 Release 附件

完成 Mac 验收、签名和公证流程后再执行。下面以 arm64 为例；Intel 使用 `x86_64`。多架构可重复传入 `--macos-dir`。

```sh
.venv/bin/python scripts/collect_release_assets.py --windows-dir ../release-assets --macos-dir output/macos/arm64 --output ../github-release-v0.11.1
```

脚本只生成本地目录，包含新 Windows 安装包、Windows 对应源码、上游源码、许可、验证清单、最终 Mac DMG 及其构建信息，并重算 SHA-256。输出目录必须尚不存在。

检查 DMG 最终状态。编辑 `docs/RELEASE_NOTES_0.11.1.md`，如实补上已验证架构、最低实测 macOS 版本及签名公证状态。默认文字不会宣称 Mac 已验收。

## 4. 创建标签和 Release 草稿

如果发布说明有改动，先提交并推送；如改变运行源码，需重新构建对应的安装包和源码附件。

```sh
git add docs/RELEASE_NOTES_0.11.1.md
git diff --cached --quiet || git commit -m "Document verified macOS release"
git push
git tag -a v0.11.1 -m "Mystery 0.11.1"
git push origin v0.11.1
gh release create v0.11.1 ../github-release-v0.11.1/* --repo SamanthaMengjunyu/Mystery --verify-tag --draft --title "Mystery 0.11.1 · 星云之间" --notes-file docs/RELEASE_NOTES_0.11.1.md
```

若标签已存在，先检查它指向预期提交，不要删除或覆盖已公开标签。草稿中核对附件和下载链接，检查后在 GitHub 点击 Publish release。setup.exe 和 DMG 均作为 Release 附件，不进入 Git 仓库。

参考：[GitHub：导入本地仓库](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github)、[GitHub CLI 建仓](https://cli.github.com/manual/gh_repo_create)、[创建 Release](https://cli.github.com/manual/gh_release_create)。
