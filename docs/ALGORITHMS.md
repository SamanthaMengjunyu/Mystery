# Mystery

从原项目 `20260310-bazi` 提取的独立 Python 算法包与桌面软件。按功能分类，可被桌面程序、Web 后端、脚本直接调用。当前 0.11.1 源码使用银白导航、中性银灰磨砂面板与香槟重点色，透光磨砂说明卡和生日提醒打破深色界面的沉闷；统一出生地搜索（城市／省份、中文／拼音／首字母与错拼）、自动只读时区、右下角生日弹窗与顶部／底部工具栏，使用透明猫眼巫师帽 Logo；保留四种命盘的图形展示：五行流转与四柱、黄道相位与日月升、紫微十二宫三方四正、印度占星 D1/D9 南印度宫盘与大运时间线，支持沉浸收起生辰侧栏、点选说明及阅读导航；已用 SiliconFlow 实测八类 AI 解读、追问对照与速览回退。桌面前端与 Windows EXE 以体积辉光主星作为生日簿入口，并加入可拖掷铜钱、洗切抽翻牌、逐步成卦和拖开书页的全窗口三维问事操作台，支持自由视角、左侧抽屉与整副牌环形展开、中央三维烛光与 78 张离线韦特插画，功能星轨围绕主星展开；默认完整粒子动效，并统一深色下拉菜单和滚动条；提供首次生辰引导、多人生日簿、命盘资料复用与节点放大过渡；可选将当次大致位置与鼠标轨迹混合到系统安全随机数中，位置仅本机使用且不保存坐标；保留有前后纵深的白色镂空球与所属轨道，以及此前全部算法、随机／回放／时间底座和可选 AI 解读。

桌面入口位于 `desktop/`，通过本机回环服务连接算法，使用 SQLite 保存个人星迹；不包含账号登录、管理员白名单或原项目凭据。原项目保持不变。生日簿现以离线三维地球管理朋友的出生地与现居地，文字搜索／地图选城联动时区，配备微光经纬网和可自定义的朋友代表色；答案之书支持一键翻开实体双页，牌环取消叠压与悬浮报号，并随机安排牌背位置和展开时序。新增本地文件夹／音频直链播放器、自转星云／地球沉浸专注；地图支持光点备注与人物／地点筛选，按朋友现居地时区提前五天及当天进行应用内生日提醒。定位统一在设置管理，默认启用但首次需授权，拒绝后仍可使用设备时区。算法包本身仍可独立使用。

项目状态与已确认的桌面 UI/UX 方向见 [项目说明](../README.md)。0.5.0 已围绕“中央单一立体星云、可探索的三维功能空间、整个 EXE 一致的纵深感”实现桌面界面。安装 `output/release/Mystery-0.11.1-setup.exe`，或直接运行便携版 `output/release/Mystery-0.11.1.exe`，使用与构建说明见 [DESKTOP.md](../DESKTOP.md)。

## 目录

```text
Mystery/
  mystery/
    randomness.py  系统安全随机、用户交互摘要、无偏抽取与旧 seed 兼容
    timebase.py    显式时区、夏令时边界、UTC 与 UTC+08 标准时转换
    bazi/          chart.py 四柱排盘；analysis.py 八字规则分析
    astrology/     engine.py 星盘排盘、时区换算、结构分析
    ziwei/         engine.py 紫微十二宫、四化、大限、流年；本地 iztro 桥接
    jyotish/       engine.py Lahiri九曜、月宿、D1/D9、Vimshottari大运子运
    ephemeris.py   两套占星共用的 Swiss Ephemeris 调用锁
    liuyao/        casting.py 起卦装卦与分析；data.py 纳甲、卦宫、卦辞等
    meihua/        casting.py 报数／农历／当地时间起卦，本互变及体用
    lenormand/     reading.py 36张牌的三／五张线性解读与回放；data.py 牌库
    tarot/         reading.py 抽牌与分析；data.py 78 张牌、牌义、牌阵
    solar_time/    calculator.py 经度时差、均时差、真太阳时、城市经度
    answers/       oracle.py 随机取答案；data.py 原有 197 条答案
    llm/           可选 AI 调用、并发调度和提示词，独立于上述算法
      prompts/     按八字、西占、紫微、印占、六爻、塔罗、梅花、雷诺曼、追问分类
  examples/        离线全功能示例、可选 AI 示例
  tests/           可在任意电脑运行的离线测试
  requirements.txt
  pyproject.toml
  SOURCE_MANIFEST.json  原始算法文件来源和 SHA-256
```

## 使用

需要 Python 3.10 或以上，已在现有 Python 3.12 环境验证。进入本目录后可直接 import，无需启动服务。

在你选定的 Python 环境中安装依赖：

```powershell
python -m pip install -r requirements.txt
```

也可将本包安装到自己的项目环境：

```powershell
python -m pip install .
```

以上命令供调用者自行执行；提取过程中没有新建环境或安装依赖。核心依赖仅保留原有的 `lunar-python`、`pyswisseph`、`tzdata`。塔罗、真太阳时、答案之书与 LLM 模块自身只用标准库，可单独导入。

新增紫微模块另需 **Node.js 18或以上**，可执行文件位于 PATH 或通过 `node_binary` 指定。Python 包已附锁定的 iztro 2.6.2 独立引擎与许可文件，排盘时不联网、不运行 npm、不安装依赖；没有 Node 时明确报错。开发验证阶段通过 npm 下载了参考依赖，均放在忽略的 `.cache/` 中，运行包不依赖该目录。印度占星复用已有 `pyswisseph`，无需新 Python 依赖。

运行离线示例和测试：

```powershell
python -m examples.quickstart
python -m unittest discover -s tests -v
```

## 功能入口

| 分类 | 导入入口 | 返回内容 |
| --- | --- | --- |
| 八字 | `mystery.bazi.calculate_bazi` | 四柱、农历、十神、藏干、纳音、五行、大运、旺衰、喜忌、格局、刑冲合害、神煞、关键看点 |
| 八字分析 | `mystery.bazi.analyze_chart` | 对已有八字 chart 重做规则分析 |
| 星盘 | `mystery.astrology.cast` | 行星、宫位、相位、日月升、命主星、元素/三态、相位格局、半球、关键看点 |
| 星盘基础 | `mystery.astrology.compute_chart` / `analyze_chart` / `to_utc` | 单独排盘、分析或历史时区换算 |
| 紫微斗数 | `mystery.ziwei.cast` / `analyze_chart` | 命身宫、十二宫星曜及四化、大限、可选指定年份流年、结构事实 |
| 印度占星 | `mystery.jyotish.cast` / `analyze_chart` | Lahiri九曜、月宿及Pada、D1/D9整宫、Vimshottari大运／子运 |
| 六爻 | `mystery.liuyao.cast` | 本卦、变卦、动爻、纳甲、六亲、六神、世应、旬空、用神旺衰、干支历参考、关键看点 |
| 三钱转换 | `mystery.liuyao.tosses_from_yang_counts` | 每次阳面数 0/1/2/3 转换为爻值 6/7/8/9 |
| 六爻自动投掷 | `mystery.liuyao.draw` / `replay` | 三钱法系统随机投掷、原始爻值、版本化快照与回放 |
| 梅花易数 | `mystery.meihua.cast_numbers` / `cast_lunar` / `cast_time` | 报数、农历、当地时间起卦，本互变、单动爻、体用关系与回放 |
| 雷诺曼 | `mystery.lenormand.draw` / `cast` / `prepare_shuffle` / `replay` | 36张牌三／五张线性牌阵、实体牌录入、相邻与镜像组合、私有洗牌及回放 |
| 塔罗 | `mystery.tarot.draw` / `prepare_shuffle` / `replay` | 牌阵、抽牌、正逆位、牌义、结构分析，支持私有洗牌快照和旧 seed |
| 牌库 | `mystery.tarot.get_deck` / `get_spread` | 韦特牌库与单张、三张、凯尔特十字牌阵定义 |
| 真太阳时 | `mystery.solar_time.to_true_solar_time` | `(校正后 datetime, 校正明细 dict)` |
| 答案之书 | `mystery.answers.draw_answer` / `replay` | 固定197页与答案映射、版本化快照；旧 seed 保持旧行为 |
| 用户参与摘要 | `mystery.randomness.interaction_evidence` | 对鼠标／触摸坐标及相对时间生成摘要，不采集设备信息 |

除真太阳时返回元组外，各主入口均返回普通 Python 字典；排盘主入口的字典可直接 JSON 序列化。不同模块可能有同名函数，建议使用别名。

### 八字

```python
from mystery.bazi import calculate_bazi

chart = calculate_bazi(
    1990, 6, 15, 12, 30,
    gender="男", longitude=116.41, use_true_solar=True, sect=2,
)
print(chart["summary"])
print(chart["analysis"])
```

输入为 `tz_name` 指定时区的当地钟表时间，默认 `Asia/Shanghai`；年份 1900～2100。现在可以直接传出生地当地时间及 IANA 时区。引擎先转换到固定 UTC+08 标准时，消除历史夏令时，再按配置做真太阳时校正；关闭真太阳时也以 UTC+08 标准时排盘。启用真太阳时必须提供经度。`sect=2` 为晚子时归当日，`sect=1` 为晚子时归次日。

如果旧调用者已提前换算为固定 UTC+08，传 `tz_name="Etc/GMT-8"`，避免历史夏令时被再次换算。历史中国夏令时出生盘可能因此与 0.1.0 改变，这是本次时间修正的预期行为。

### 星盘

```python
from mystery.astrology import cast as cast_astrology

chart = cast_astrology(
    1990, 6, 15, 12, 30,
    lat=39.90, lon=116.41, tz_name="Asia/Shanghai", house_system="P",
)
print(chart["analysis"]["big_three"])
```

此处输入的是出生地当地时间，`tz_name` 用 IANA 时区名，按历史规则换算 UTC。八字、西占与六爻共用时间解析：不存在的当地时间拒绝处理；重复时刻必须明确 `fold=0`（第一次）或 `fold=1`（第二次）。宫制支持 `P/W/K/E`。使用 Swiss Ephemeris 的 Moshier 内置星历，不需要额外星历数据文件。极地纬度等场景可能不适用部分宫制，底层计算异常沿用原行为。

### 六爻

```python
from mystery.liuyao import cast as cast_liuyao

reading = cast_liuyao(
    [6, 7, 8, 9, 7, 8],  # 从初爻到上爻，自下而上
    question="近期工作如何？", category="career",
    date={"year": 2026, "month": 10, "day": 15, "hour": 12},
)
print(reading["ben"]["name"], reading["dong"])
```

爻值为 6 老阴、7 少阳、8 少阴、9 老阳；6 和 9 为动爻。日期不填时明确取 `tz_name` 当前时刻，默认 `Asia/Shanghai`，不再使用服务器本地时间。显式日期必须包含年月日，小时／分钟／秒不填时均为0；历法统一以 UTC+08 标准时计算，保留到秒，`date` 返回的是历法计算时刻，`time` 保存原输入时区与 UTC。分类键为 `zonghe/career/wealth/love/health/study/children/travel`。

### 塔罗、真太阳时、答案之书

```python
from datetime import datetime
from mystery.tarot import draw
from mystery.solar_time import to_true_solar_time
from mystery.answers import draw_answer

tarot = draw("three", seed=12345, picks=[0, 20, 77])
corrected, detail = to_true_solar_time(datetime(1990, 6, 15, 12, 30), 116.41)
answer = draw_answer("试试？", seed=12345)
```

塔罗牌阵键为 `single/three/celtic`。相同显式 seed、牌阵、选牌位置保持旧版牌与正逆位结果；不填 seed 时直接使用系统安全随机，不再用48位 seed 驱动普通伪随机。可用 `reversals=False` 关闭逆位。保留牌数据中的 `img` 文件名供未来接入界面，本包不附带图片，也不读取图片。

真太阳时保留原有经度时差与 NOAA 均时差近似公式。独立函数接收无时区 datetime 且不传 `tz_name` 时，仍解释为固定 UTC+08；传入 aware datetime 或 `tz_name` 时先完成时区转换，返回无时区的太阳时及 UTC+08 校正明细。

答案之书默认在197页中随机选一页，第 N 页固定对应 `ANSWERS[N-1]`；显式 seed 仍保留旧版1～888装饰页码与答案独立随机的行为。两种规则通过快照 schema 区分；问题文字均不参与选择，其 Python seed 不对应旧浏览器随机状态。

### 系统随机、用户参与和回放

```python
from mystery.randomness import interaction_evidence
from mystery.tarot import prepare_shuffle, draw, replay as replay_tarot
from mystery.liuyao import draw as draw_liuyao, replay as replay_liuyao

# 由未来的客户端在抽取操作区域采集，这里只是接口示例。
# x/y 相对区域宽高归一化到0～1；t_ms 为同一次操作内的相对毫秒时间。
evidence = interaction_evidence(
    [{"x": 0.2, "y": 0.8, "t_ms": 0}, {"x": 0.7, "y": 0.3, "t_ms": 83.5}],
    device_time="2026-10-15T12:00:00+08:00", app_version="0.2.1",
)

# 准备洗牌后将其留在服务端，同一轮后续点选复用这个对象。
shuffle = prepare_shuffle(interaction=evidence)
reading = draw("three", picks=[0, 20, 77], shuffle=shuffle)
restored = replay_tarot(reading["replay"], question=reading["question"])
assert restored == reading

liuyao = draw_liuyao(interaction=evidence)
assert replay_liuyao(liuyao["replay"]) == liuyao
```

- 无用户交互时使用 `secrets.randbelow`；有交互时，逐次取得新的32字节系统随机，用 HMAC-SHA256 混合交互摘要、用途和计数器，再用拒绝采样消除取模偏差。没有自建 seed 伪随机流，也不宣称通过 NIST 认证。
- 六爻模拟18枚独立公平币，六次自下而上，`6/7/8/9` 概率为 `1:3:3:1`。实体投币继续使用 `cast(tosses, ...)`，标记来源为 `manual`。
- 交互输入最多4096个样本，时序不得倒退，相对时间限定在24小时内。仅记录轨迹摘要、样本数、可选上下文摘要，不记录原始轨迹。摘要只是调用者所提供内容的关联标识，不保证匿名、真人操作或前端数据真实性，也不是阻止服务端重抽的公平性证明。
- 不主动采集内网IP、设备标识或系统版本。设备时间和应用版本可选，作为上下文参与混合；它们不被计为熵，也不代替系统随机或排盘时区。
- 输入无鼠标轨迹完全可用，触屏可提供相同坐标格式。当前包没有前端采集、硬件／物理随机设备接入或结果数据库，快照需由调用者保存。
- `random` 保存来源、算法版本、用户参与摘要；`replay` 保存结果快照、规则版本。回放不产生新随机，题目可另传。塔罗快照包含全副牌序和逆位，**选牌结束前必须只在服务端保存，客户端只拿不透明会话ID**；不能把快照或旧 seed 暴露给尚在选牌的客户端。
- 塔罗新快照 `tarot-reading-v2` 校验牌库与牌阵摘要；六爻新快照 `liuyao-reading-v2` 校验规则表、历法依赖版本与完整时间记录，变化时拒绝静默重算。答案之书校验答案池摘要。旧 v1 快照仍能回放，并保留 v1 标记；它们缺少的历史摘要无法补证。
- 回放会校验随机来源记录的字段、用途和算法是否一致，但快照不带签名，仍只适合可信存储；不能直接信任客户端提交的牌序／来源标签。静态数据、分析代码或历法依赖升级时须保留兼容版本引擎。所有新结果与快照可 JSON 序列化。

0.2.1 补齐接口边界：未知牌组、宫制、六爻分类与无效八字规则选项明确报错；裸 `compute_chart` 也执行完整参数校验。六爻在第一枚随机币之前固定问事时刻。带 `ZoneInfo` 的 aware datetime 也会校验是否落在不存在的时间，防止绕过 naive 时间检查。

随机来源参考：[Python secrets](https://docs.python.org/3/library/secrets.html)；客户端坐标采集接口可参考 [W3C Pointer Events](https://www.w3.org/TR/pointerevents3/)。

## 紫微斗数与印度占星

```python
from mystery.ziwei import cast as cast_ziwei
from mystery.jyotish import cast as cast_jyotish

ziwei = cast_ziwei(
    2000, 8, 16, 4, 0, "女",
    tz_name="Asia/Shanghai", fix_leap=True,
    day_divide="forward", year_divide="normal", target_year=2026,
)
print(ziwei["summary"], ziwei["analysis"]["natal_mutagens"])

jyotish = cast_jyotish(
    2000, 4, 28, 5, 50, lat=40.7, lon=-74,
    tz_name="America/New_York", node_mode="mean", dasha_year="sidereal",
)
print(jyotish["d1"]["lagna"], jyotish["d9"]["lagna"])
print(jyotish["vimshottari"]["at_birth"])
```

两者均使用当地阳历出生时间，接受 `fold` 处理夏令时重复时刻，出生年份1900～2100。返回普通字典，可 JSON 序列化，并包含 `module/input/time/rules/summary/analysis`。

紫微首版固定 iztro 通行安星规则和其原版四化／亮度表；`palaces` 保留上游字段名及完整星曜数据，`birth` 保存农历、命身宫地支、命主身主及五行局。默认农历正月初一换年（`year_divide="normal"`，可选立春 `exact`）、晚子归次日（`day_divide="forward"`，可选当日 `current`）、闰月前后半月调整（`fix_leap=True`）。运限年界和虚岁规则固定为上游 `normal`，全部配置记入结果。

紫微先转换为 UTC+08 标准时；默认不校正真太阳时，启用时传 `use_true_solar=True, longitude=...`。`calculation_time` 记录实际排盘日期和时辰索引。大限返回12步。流年必须显式指定 `target_year`，范围为排盘出生年到2200，固定取该年6月1日午时作为年盘参考；不填则 `annual=None`，不会偷取今天。首版没有流月／流日／流时分析，也不推断出生时辰。

印占固定 Lahiri 恒星黄道，使用 Swiss Ephemeris Moshier，直接从当地时间转换 UTC，不对天文瞬间套用真太阳时。九曜为日月、水金火木土、Rahu/Ketu；节点支持 `mean/true`，Ketu 与 Rahu 相差180度。D1/D9 均用整宫制；D9 为传统 Parashari 九分法，所有边界以未舍入黄经计算。`grahas` 为九曜与27月宿／四Pada，`d1/d9` 为分盘，`analysis` 仅输出命主星位置、月宿、同星座分盘等可复算事实，不生成复杂瑜伽或吉凶评分。

Vimshottari 从月亮所在月宿计算出生大运余额，返回出生所属大运完整起点开始的一轮120年（含出生前已过去部分），每个大运含九个子运，日期区间左闭右开。`at_birth` 仅表示出生时的运限，不是当前运势。年长默认 `sidereal=365.25636` 天，可选 `julian=365.25` 或 `savana=360`，记录在规则中；不同软件采用不同年长时，具体运限日期会不同。没有隐式当前日期、其他岁差体系、更高分盘、合婚或出生校时。

两套占星通过共享锁协调本包对 Swiss Ephemeris 的调用；印占显式设置 Lahiri，不改变西占返回的热带黄道规则。外部代码直接使用 Swiss Ephemeris 的配置不受该锁管理。

运行新入口离线示例：`python -m examples.new_charts`。紫微资料来源及许可见 `mystery/ziwei/vendor/manifest.json`、`iztro-LICENSE.txt` 和 `THIRD_PARTY_NOTICES.txt`；独立包源为 [iztro](https://github.com/SylarLong/iztro)。印占计算定义与验证示例参考 [P.V.R. Narasimha Rao 教材](https://vedicastrologer.org/articles/vedic_astro_textbook.pdf) §6.2.9、§16.2；首版是独立公式实现，没有引入 PyJHora。现有 Swiss Ephemeris 及 Python 包装器的许可约束继续适用。

## 梅花易数与雷诺曼问事

```python
from mystery.meihua import cast_numbers, cast_time, replay as replay_meihua
from mystery.lenormand import draw, cast as read_cards, replay as replay_lenormand

# 明示三数法：前两数取上下卦，第三数独立取动爻，不加今天的时间。
meihua = cast_numbers(34, 43, 1, question="这次合作需要关注什么？")
timed = cast_time(2026, 10, 15, 12, question="沟通应如何推进？", tz_name="Asia/Shanghai")
cards = draw("five", question="合作中的沟通与约定需要关注什么？")
physical = read_cards([27, 25, 24], question="这份约定如何沟通？")
assert replay_meihua(meihua["replay"]) == meihua
assert replay_lenormand(cards["replay"]) == cards
```

梅花入口是确定性取象，不使用随机数。八卦顺序为乾1、兑2、离3、震4、巽5、坎6、艮7、坤8；除8余0取8，除6余0取6，爻从下到上。

- `cast(upper, lower, moving_line)` 直接接收1～8先天卦数与1～6动爻。
- `cast_numbers(first, second, third=None)` 接收0～2147483647的整数。两数法以前两数分别除8定卦，以两数和除6取爻；三数法第三数独立除6取爻。这是本包明示的报数配置，不宣称是唯一古法。两数法可显式加 `hour_number=1..12`，作为两数与时数之和取爻；不能与第三数混用，不会偷取当前时辰。
- `cast_lunar(year_branch, month, day, hour_branch, leap_month=False)` 依传统年月日时数起卦。年／时地支传子至亥，编号1～12；年月日之和取上卦，加时数取下卦与动爻。闰月沿用该月数字。此入口没有完整农历年份，只校验月日数值范围，不能验证该日是否真实存在。
- `cast_time(...)` 接收1900～2100的显式阳历当地时间，使用共享时区／fold校验，转换为UTC+08标准时后换农历。按农历春节换年、午夜00:00换日，23点与0点均为子时；不使用立春换年、不加真太阳时，不默认今天。

梅花单动爻所在的经卦为用，另一卦为体；变卦中的体保持同一位置。互卦取二三四爻为下、三四五爻为上。`nuclear="classic"` 默认在纯乾／纯坤时改取变卦之互，这是本包对“乾坤无互，互其变卦”的选定口径；`nuclear="standard"` 总取本卦中爻。两种均记录来源，不隐去流派差异。互卦完整卦名只作核对，主要依据上下互卦。

梅花输出 `ben/hu/bian/moving_line/analysis`，体用分析只列五行生克关系，不套用六爻纳甲、世应、六亲、六神，也不生成吉凶分数或精确应期。`random=None`，来源与逐步数值在 `source/trace`；回放检查相关卦表、规则及时间记录。`replay` 默认保留问题，可用 `question=...` 改写问题而不改卦。

雷诺曼使用36张Petit Lenormand，牌编号1～36，无正逆位。三张／五张采用本包 `project-linear-v1`：按左至右串联，中牌为焦点，相邻牌有顺序；镜像分别是一三或一五／二四，不直接等同于过去未来。`cast` 录入实体牌或外部已定牌序，标为手动来源，`random=None`；`draw` 复用系统安全随机与交互摘要底座，无放回抽取。`seed` 是显式的可复现模拟模式。

雷诺曼的中文关键词、主题标签和20条有序组合提示由本项目编写，作为首版有限规则集，不是完整传统组合词典，也不复制商业牌书。组合未命中时 `has_selected_rule=False, reading_hint=None`，仅保留关键词，供模型结合问题作条件性解释；没有假装每一对牌都有专门规则。人物牌不自动绑定用户性别，也不推断图像朝向。

`prepare_shuffle()` 支持同一副私有洗牌后续点选，`draw(..., picks=[0, 20, 35], shuffle=...)` 以0～35槽位抽牌。洗牌及回放对象含整副隐藏牌序，选择完成前留在服务端；不直接发送给客户端。回放检查牌库、牌阵、组合规则和随机来源，并核对保存牌与槽位一致。两类回放仍要求可信存储，摘要不等于签名。

两类返回结果可JSON序列化，无新增依赖；梅花使用现有农历依赖，雷诺曼自身仅使用标准库。运行 `python -m examples.question_methods` 查看离线示例。本阶段没有增加文字笔画起卦、自动外应采集、雷诺曼大牌阵或新前端。

规则及例子参考 [《梅花易数》卷一原文](https://zh.wikisource.org/wiki/梅花易數/卷一)；雷诺曼36张体系可参见 [大英博物馆馆藏](https://www.britishmuseum.org/collection/object/P_1896-0501-413)，组合方向存在不同实践口径，参见作者的 [Directionality](https://www.lenormandreader.com/blog/directionality-with-lenormands-cards)。本包采用的读法与有限提示以记录的规则为准。

## 可选 AI 解读

排盘与结构分析完全离线，不需要 Key。`mystery.llm.prompts` 也可以在离线情况下生成提示词，接入自己的 AI 客户端：

```python
from mystery.llm.prompts import build_prompt, build_followup_messages

system, user = build_prompt(chart)  # 此处 chart 应是八字 calculate_bazi 的结果
messages = build_followup_messages(
    "bazi", chart, "此前的解读", [], "事业方面还有什么建议？",
)
```

内置客户端仅支持 OpenAI 兼容的 `/chat/completions` 与 `/models`。必须由调用者显式提供 API 根地址、Key、模型，没有默认厂商、地址或模型，不会自动读取旧项目配置，也不保存凭据。

```python
from mystery.llm import make_config, interpret_tarot_stream

# api_base、api_key、model_id 由你的程序从用户输入或环境变量中获取。
# api_base 是 API 根地址；不要填写完整的 /chat/completions 地址。
cfg = make_config(api_base, api_key, model_id)
for event in interpret_tarot_stream(tarot, cfg):
    if event["type"] == "delta":
        print(event["text"], end="")
```

也可自行设置 `LLM_API_BASE`、`LLM_API_KEY`、`LLM_MODEL` 后运行 `python -m examples.llm_example`。只有显式运行该联网示例或调用客户端才会发送请求。

流式入口包括 `interpret_chart_stream`、`interpret_astro_stream`、`interpret_tarot_stream`、`interpret_liuyao_stream`、`interpret_followup_stream`；另有八字非流式 `interpret_chart`。事件类型沿用 `queue/notice/delta/usage/error`；无兜底时的请求失败仍可能抛 `RuntimeError`，调用者应捕获。`usage` 是模型实际返回的 token 用量，不自动落库。

紫微／印占新增 `build_ziwei_prompt`、`build_jyotish_prompt`，以及 `interpret_ziwei_stream`、`interpret_jyotish_stream`；导入位置与其他提示词／流式入口一致。追问 `module` 新增 `ziwei/jyotish`。提示词以已排出的事实为依据，不允许模型更改星曜、分盘或运限；离线生成提示词不发送网络请求。本次没有调用真实模型验证其解读质量。

梅花／雷诺曼提供 `build_meihua_prompt`、`build_lenormand_prompt` 与 `interpret_meihua_stream`、`interpret_lenormand_stream`，追问支持 `module="meihua"/"lenormand"`。模型只能解释已定卦或牌；雷诺曼提示词不会带入完整私有牌序，区分命中的规则提示和模型生成的条件性解释。

默认关闭速览兜底。启用时使用 `make_config(..., lite_model=your_lite_model, fallback=True)`。并发调度沿用原有的进程内实现：首次流式调用固定并发槽位，之后修改配置不会重新建立槽位；它不隔离不同用户，不包含账号系统或记录存储。

## 提取原则与验证

0.1.0 提取时保留原排盘、分析规则、牌库、卦表和主要返回字段；0.2.x 对默认随机、时间解析、回放和来源表述作了上述修改，0.3.0 新增紫微和印度占星，0.4.0 新增梅花和雷诺曼。原管理员配置改成显式参数，不搬运任何私人数据。`SOURCE_MANIFEST.json` 仍记录初次提取的原始源文件，不能用作当前实现逐字一致的证明。

测试包含四柱与五行、晚子时、太阳时跨日、历史夏令时、四种宫制、64 卦覆盖、动爻翻转、牌库完整性、选牌复现、提示词、连接参数校验，以及用模拟响应验证 LLM 非流式、流式、用量和断线兜底。测试不会调用真实模型或消耗额度。与原项目的计算结果对照记录见 `VALIDATION.md`。

这是算法整理，不是对传统规则准确性的重新论证；保留原有公式、流派、适用范围和限制。
