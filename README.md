# English Interview Clipper

把一条 YouTube 访谈（科技大佬等）变成竖屏 1080x1920 英语学习视频：
逐句中英字幕、生词栏（四级→雅思难度）、自动封面，并发布到抖音。

这是 [Muse skill](https://muse.ai)，把本仓库作为 skill 安装即可使用。

## 安装

```bash
pip install -r requirements.txt
# 系统依赖：ffmpeg，Noto Sans CJK 字体
#   Debian/Ubuntu: apt install ffmpeg fonts-noto-cjk
python run.py --build-exam-words   # 一次性：下载 ECDICT 生成 exam_words.json
```

翻译二选一：

- 在线（质量最好）：设置环境变量 `TRANSLATE_BASE_URL` / `TRANSLATE_API_KEY` / `TRANSLATE_MODEL`
- 离线：`argospm install translate-en_zh`

## 使用

```bash
python run.py --url https://www.youtube.com/watch?v=XXXX
```

流程：下载（优先 1080p）→ 转写 → 翻译 → 内容审查 → 生词提取 →
样张确认 → 全片渲染 → 封面（3:4 + 4:3）→ 推送到抖音（需人工确认）。

完整产品规范见 [SKILL.md](SKILL.md)。

## 版式（1080x1920，固定）

- 生词栏 y=170（灵动岛安全区下方），跟随语音滚动，居中
- 访谈画面 1080x608，y=610
- 英文字幕 y=1300（生词黄字加粗），中文字幕 y=1440（金色），逐句显示、互不覆盖

## 关键规则（不要改弱）

- 片源 ≥720p，优先 1080p
- 片头 logo 动画必剪；首帧残影必查（t=0/0.1/0.15）
- 角落烧录 logo 做模糊，不打黑块
- 全片字幕审查：涉华负面言论整段剪掉
- 生词：排除四级词（ECDICT）+ 词频 zipf>4.6，雅思词优先，按片内词频取 top 108；每个词必须有中文释义（缺失则渲染直接报错），生词栏中英对照、等宽对齐
- 每集正片≤55分钟 + 4秒进群片尾（总时长<59分钟）；超1小时按整句边界分集
- 每个视频生成 `{标题}.xlsx` 生词清单（序号|单词|中文|次数），发粉丝群下载
- **运行生词提取的 Python 必须装有 wordfreq，缺失则直接报错退出，绝不静默跳过**
