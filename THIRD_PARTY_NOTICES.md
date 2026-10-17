# 第三方代码与素材

Mystery 的项目许可证仅适用于项目权利人有权授权的内容。第三方代码、运行时和数据保留各自的许可证和版权声明。发布二进制时，应同时分发对应许可和所需源码；`licenses/` 是交接时从现有 Windows 发行目录汇总的许可副本，Mac 构建还需收集该平台实际安装的依赖许可。

| 组件 | 用途和版本 | 许可及文件 |
| --- | --- | --- |
| pyswisseph / Swiss Ephemeris | 占星，2.10.3.2 | AGPLv3；`licenses/pyswisseph-LICENSE.txt`；源码压缩包随交接包提供 |
| lunar-python | 历法，1.3.12 | MIT；`licenses/lunar-python-LICENSE` |
| Three.js / OrbitControls | 三维界面，0.180.0 | MIT；`desktop/web/vendor/LICENSE` |
| iztro | 紫微引擎，2.6.2 | MIT；`mystery/ziwei/vendor/iztro-LICENSE.txt`；其内嵌依赖声明同目录 `THIRD_PARTY_NOTICES.txt` |
| pywebview | 原生窗口，6.2.1 | BSD；`licenses/pywebview-LICENSE` |
| Node.js | 内嵌紫微运行时，现有 Windows 包为 24.14.0 | Node 及所含组件许可；`licenses/Node-LICENSE.txt`；Mac 应使用所选 Node 版本自己的 LICENSE |
| tzdata | IANA 时区，2026.2 | `licenses/tzdata-LICENSE` 和 `tzdata-LICENSE_APACHE` |
| tzfpy | 离线时区查询，2.1.1 | MIT 与数据声明；`desktop/licenses/tzfpy-*` |
| timezone-boundary-builder | tzfpy 内附时区边界 | ODbL；`desktop/licenses/Timezone-Data-*`、`tzfpy-NOTICE` |
| GeoNames | 城市和省域参考点 | CC BY 4.0；`desktop/licenses/Geography-NOTICE.txt` |
| Natural Earth | 陆地与国家轮廓 | 公有领域；同上 |
| Rider-Waite-Smith 牌面 | 78 张原版扫描 | 原始作品公版；保留扫描项目 MIT 许可及署名，`desktop/licenses/Tarot-RWS-*` |
| pypinyin / OpenCC | 离线索引生成工具 | MIT / Apache-2.0；`desktop/licenses/pypinyin-LICENSE.txt`、`OpenCC-LICENSE.txt` |
| pythonnet / clr_loader / cffi | Windows 桌面依赖 | `licenses/` 中对应 LICENSE |
| Python / PyInstaller | 解释器与冻结程序引导器 | `licenses/Python-LICENSE.txt`、`PyInstaller-COPYING.txt`（包含引导器例外）；Mac 需使用实际 Python 发行版的许可 |

## 数据与图像来源

GeoNames 数据提取了名称、别名、经纬度、人口与时区；中文索引使用 OpenCC 和 pypinyin 生成。Natural Earth 国家轮廓保留名称和几何，坐标经过舍入。来源、日期、适配说明和 SHA-256 位于 `desktop/web/assets/geography/*manifest.json`。ODbL 数据声明列出的上游与对应版本应随发行保留；如重建边界数据，还需保留可获取的对应数据及修改说明。

韦特作品绘画为 Pamela Colman Smith，设计为 Arthur Edward Waite。扫描来源与逐图哈希见 `desktop/web/assets/tarot-rws/manifest.json` 和 `desktop/licenses/Tarot-RWS-NOTICE.txt`。

星云纹理和应用 Logo 为项目提供的生成图像；提示词和生成记录保留在 `desktop/web/assets/`。Logo 的输入图另随源码保留为 `20261016-141343.png`，用于核对来源，不是运行依赖。

算法最初从 `20260310-bazi` 提取，映射和原文件哈希见 `SOURCE_MANIFEST.json`。发布者应确保有权授权这些原始代码及自有素材；本清单不替代第三方许可原文。

## 上游链接

- [pyswisseph 项目及许可证](https://pypi.org/project/pyswisseph/)
- [Swiss Ephemeris](https://www.astro.com/swisseph/)
- [iztro](https://github.com/SylarLong/iztro)
- [Three.js](https://github.com/mrdoob/three.js)
- [pywebview](https://github.com/r0x0r/pywebview)
- [GeoNames](https://www.geonames.org/)、[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- [Natural Earth 使用条款](https://www.naturalearthdata.com/about/terms-of-use/)
- [timezone-boundary-builder](https://github.com/evansiroky/timezone-boundary-builder)
- [韦特扫描来源](https://github.com/metabismuth/tarot-json)
