# 每日剧本 · SPX / SPY / QQQ

一个**全免费、零服务器**的每日交易剧本网站:每个美股交易日自动拉取
SPX / SPY / QQQ 日线和 VIX,计算关键价位(轴心点)、预期波动区间与情景树,
发布到 GitHub Pages。

> ⚠️ 本工具只展示技术面市场结构,**不构成投资建议**,也不是买卖指令。
> 末日期权(0DTE)风险极高、可在数分钟内归零。盈亏自负。

---

## 文件结构

```
playbook/
├── index.html                      网页(读取 playbook.json 渲染)
├── playbook.json                   数据文件(由脚本生成;仓库里先放了一份示例)
├── requirements.txt                Python 依赖
├── scripts/
│   └── generate_playbook.py        计算引擎:拉数据 → 算价位 → 写 json
└── .github/workflows/
    └── update-playbook.yml         定时任务:每交易日自动跑脚本并提交
```

---

## 部署步骤(约 10 分钟,不用写代码)

### 1. 建仓库
- 注册 / 登录 GitHub,点右上角 **+ → New repository**。
- 名字随意(如 `daily-playbook`),选 **Public**(公开仓库才能免费用 Pages)。

### 2. 上传文件
- 进入新仓库,点 **Add file → Upload files**。
- 把本文件夹里的所有内容**连同子文件夹**一起拖进去(`scripts/` 和
  `.github/` 这两个文件夹要保留,别拍平)。如果网页拖拽不方便保留文件夹,
  用 GitHub Desktop 或 git 命令推送最稳妥。
- 提交(Commit changes)。

### 3. 开启 Pages(托管网页)
- 仓库 **Settings → Pages**。
- **Source** 选 **Deploy from a branch**,Branch 选 **main**、目录 **/(root)**,Save。
- 等一两分钟,页面顶部会给出网址,形如
  `https://你的用户名.github.io/daily-playbook/` —— 这就是你的网站。
  此时它读的是仓库里那份**示例** playbook.json。

### 4. 开启自动更新(定时任务)
- 仓库 **Settings → Actions → General**,确保 Actions 是启用状态。
- 切到顶部 **Actions** 标签 → 左侧选 **Update Daily Playbook**
  → 右侧 **Run workflow**,手动跑一次。
- 跑完后它会用**真实数据**重新生成 `playbook.json` 并提交,Pages 自动重建。
  刷新你的网址,徽章会从"示例数据"变成"实时"。
- 之后每个交易日(默认美东开盘前)它会自动跑,你什么都不用管。

---

## 常见问题

**改自动运行时间?**
编辑 `.github/workflows/update-playbook.yml` 里的 `cron: "0 12 * * 1-5"`。
格式是 `分 时 日 月 周`,用 **UTC** 时间。`0 12 * * 1-5` = 每周一到周五 UTC 12:00。
美东有夏/冬令时,差一小时,按需调整。

**加 / 减标的?**
编辑 `scripts/generate_playbook.py` 顶部的 `TICKERS` 列表,照着已有格式加一行即可。

**网页显示"还没有 playbook.json"?**
说明定时任务还没成功跑过。去 Actions 手动 Run 一次;或在本地装好 Python 后运行
`python scripts/generate_playbook.py --mock` 生成一份示例再上传。

**Gamma 状态为什么显示"需 GEX 数据"?**
当前版本(v1)只用免费的价格+VIX 数据,没接期权链持仓量(OI),所以无法精确判断
正/负 Gamma。这是下一步可以加的功能(SPY/QQQ 链相对好拿,SPX 较难/需付费数据源)。

**自动跑了几天后停了?**
GitHub 对**长期无人改动**的仓库会暂停定时任务;本项目每天有自动提交,通常能保持活跃。
若被暂停,去 Actions 页面手动 Run 一次即可重新激活。

---

## 本地运行(可选)

```bash
pip install -r requirements.txt
python scripts/generate_playbook.py          # 拉真实数据
python scripts/generate_playbook.py --mock    # 用示例数据,不联网
# 然后用任意静态服务器打开,例如:
python -m http.server 8000                    # 浏览器访问 http://localhost:8000
```

> 注:`generate_playbook.py` 的**数据获取**部分需要联网访问 Yahoo / Stooq,
> 已内置"yfinance 主、Stooq 备"的容错。首次部署后建议先手动 Run 一次确认数据正常。
