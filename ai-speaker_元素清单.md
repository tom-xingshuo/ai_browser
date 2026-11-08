# ai-speaker.net/zh 元素识别清单

- 页面：https://ai-speaker.net/zh
- 标题：在线免费文字转语音 - AI speaker
- 页面性质：Next.js 风格 + Tailwind 的 TTS 免费工具页，无框架 id，主要靠 class 定位
- 采集方式：真实浏览器打开后读取 DOM（DOM 树 + 计算样式 + 可见性）

## 一、核心可操作元素（默认可见）

| # | 区域 | 元素 | 定位方式（推荐顺序） | 关键属性 / 文本 | 当前状态 |
|---|---|---|---|---|---|
| 1 | 文本输入 | 合成文本框 | `textarea[placeholder="输入要合成文本"]` | 无 id/name，class `textarea block w-full flex-1 ...` | 可见、可输入；XPath `/div[1]/div[2]/div[1]/div[2]/textarea[1]` |
| 2 | 文本输入 | 字数计数 | `#main .absolute.right-4.bottom-2` | 文本 `0/5000`（输入后变 `11/5000`） | 可见，纯展示 |
| 3 | 主按钮 | 文本合成语音 | `button.btn-primary`（唯一）；文本 `文本合成语音` | class `btn-primary h-10 ...` | 可见；**空文本时 disabled，输入后自动 enabled**（已验证） |
| 4 | 声音 | 当前音色选择入口 | `#main .voice-name`（title="选择声音"），文本 `晓晓` | 内含 `img` 头像 + `span.val` | 可见；点击弹出「选择声音」弹窗 |
| 5 | 参数 | 语速 | `#main .actions .voice-attr:nth-of-type(2)`（`.actions` 下第 2 个 `div`） | 文本 `1x`，图标 `icon-sudu-copy` | 可见；点击弹出滑杆浮层 `.com-progress` |
| 6 | 参数 | 音调 | `#main .actions .voice-attr:nth-of-type(3)` | 文本 `1x`，图标 `icon-a-yintiaoshengtiao` | 可见；同上 |
| 7 | 参数 | 音量 | `#main .actions .voice-attr:nth-of-type(4)` | 文本 `100%`，图标 `icon-yinliang` | 可见；同上 |
| 8 | 账号 | 登录入口 | `#main .actions .act`，文本 `登录` | class `act cursor-pointer text-primary` | 可见；div 非 button，无 role，需按文本点 |
| 9 | 头栏 | 语言切换按钮 | `#switch-lang`（id 唯一），文本 `zh` | 点击展开语言下拉 | 可见 |

## 二、交互后才出现的元素（DOM 中存在，默认 display:none）

### 2.1 声音选择弹窗 `.voice-select`（点击 #4 出现）

注意：`.voice-select` 全页有 3 个同名节点（含登录弹窗复用同一 class），选择器要加 `:not(.user-login-win)` 或直接用内部特征。

| 元素 | 定位方式 | 状态 / 说明 |
|---|---|---|
| 弹窗容器 | `.voice-select:not(.user-login-win) .select` | 隐藏，点击音色入口后显示 |
| 关闭按钮 | `.voice-select .close-btn`，文本 `×` | 隐藏 |
| 语言筛选 | `.voice-select select`（原生 select，79 个 option） | 隐藏；option value 为 `1=中文`、`2=英语`… |
| 性别筛选 | `.voice-select .custom-select` 第 1 个，文本 `全部 男声 女声` | 隐藏；自定义下拉（div），非 select |
| 级别筛选 | `.voice-select .custom-select` 第 2 个，文本 `全部 免费 Vip` | 隐藏；自定义下拉 |
| 音色列表 | `.voice-select .speakers` > `li`（42 项） | 隐藏；`li.cur` 为当前选中；每项 `.name`（晓晓/云扬/晓伊…）、`.tags`（普通话/青年女性…）、播放图标 `span.icon-bofang` |
| 数量 | `.voice-select .speaker-num .code`，文本 `42` | 隐藏 |
| 单项错误提示 | `li .error`，文本 `故障中，开发人员正在抢修!` | `display:none`，仅音色异常时才显示，正常时可忽略 |

### 2.2 登录弹窗 `.voice-select.user-login-win`（点击 #8 出现）

| 元素 | 定位方式 | 状态 / 说明 |
|---|---|---|
| 弹窗容器 | `.user-login-win`（唯一） | 隐藏 |
| 标题 / 关闭 | `.user-login-win .h3`（登录）、`.user-login-win .close-btn`（×） | 隐藏 |
| 邮箱输入 | `.user-login-win input[placeholder="请输入邮箱!"]` | 隐藏；无 id/name，只能靠 placeholder |
| 验证码输入 | `.user-login-win input[placeholder="请输入验证码"]` | 隐藏；同上 |
| 发送验证码 | `.user-login-win button.send`，文本 `发送` | 隐藏；初始 disabled，邮箱合法后才可点 |
| 提交 | `.user-login-win button`（非 `.send`），文本 `提交` | 隐藏 |

### 2.3 合成完成后的播放/下载区 `.down-block`（合成成功后出现）

| 元素 | 定位方式 | 状态 / 说明 |
|---|---|---|
| 容器 | `.down-block`（唯一） | 当前隐藏；合成完成后显示 |
| 播放器 | `.down-block audio` | 初始无 src，完成后写入音频 URL，`autoplay controls` |
| 下载按钮 | `.down-block button.btn-default` | 初始 `disabled`；可用后内含 `span.icon-xiazai1` + `span[title="下载音频"]` |
| 参数滑杆浮层 | `#main .actions .voice-attr .com-progress` | 点击语速/音调/音量后动态插入，含 `.progress-title`、`.progress-body` |

## 三、导航与链接（可见）

| 元素 | 选择器 | 文本 / 目标 |
|---|---|---|
| 站内 Logo | `header a[href="/"]` | AI speaker |
| 语言下拉项 | `a[href="/en"] /zh /tw /ja /ko /pt /es /de /fr /it /ar /nl /pl` | 默认隐藏，点 `#switch-lang` 后出现 |
| Edge 扩展 | `a[href*="microsoftedge.microsoft.com"]` | Edge 扩展下载 |
| Chrome 扩展 | `a[href*="chromewebstore.google.com"]` | Chrome 扩展下载 |
| Android | `a[href*="play.google.com"]` | Google Play |
| iOS | `a[href*="apps.apple.com"]` | App Store |
| 页脚 | `a[href="/pricing"]`、`a[href="/agreement"]`、`a[href="/privacy"]`、`a[href^="mailto:"]` | 定价 / 服务协议 / 隐私政策 / 邮箱 |

## 四、未使用 / 可忽略

- 无原生 checkbox / radio / switch
- 无 `role=dialog` 节点，弹窗靠 class 控制
- iframe 仅 3 个：Google 广告（`doubleclick.net`）、`recaptcha/api2/aframe`，均隐藏且与业务无关
- 隐藏的 `input[type=file].hide`：不在主流程
- 页面无 id 体系的表单字段（除 `#main`、`#switch-lang`），后续建议以 `placeholder` / 文本 / class 组合为主

## 五、验证进度与阻塞点

已验证：
- 页面可正常打开（HTTP 正常，无验证码拦截）
- 文本框可输入，字数计数联动（`11/5000`）
- 「文本合成语音」按钮从 disabled → enabled 的联动确实存在

无法验证（环境限制，非站点问题）：
- 本次浏览器会话视口为 `0×0`（窗口为最小化/零尺寸），真实鼠标点击全部被拒绝（coordinates outside the visible viewport），因此以下均未能实际触发：
  - 点击「文本合成语音」后是否弹登录、是否直接合成
  - 声音选择弹窗、语速/音调/音量浮层、登录弹窗的实际显示
  - 合成完成后的 `.down-block`、`audio[src]`、下载按钮可用状态
- 通过 Tab 聚焦按钮 + Enter 触发也未产生合成请求，判断同样受零尺寸视口影响，不能据此得出「必须登录」的结论

待确认事项（需要一次正常窗口的点击验证）：
1. 匿名状态点击合成是否直接出音频（页面对未登录用户显示 `0/5000` 配额，推测可免登录合成）
2. 下载按钮是浏览器下载事件，还是基于 `audio` 的 blob/直链（决定后续用 `expect_download` 还是直接请求 `audio.src`）
3. 生成中的按钮文案/进度提示（用于自动化等待断言）

## 六、后续自动化建议（写脚本时用）

1. 等待输入就绪：`page.wait_for_selector('textarea[placeholder="输入要合成文本"]')`
2. 填文本：`fill` 后断言 `button.btn-primary` 由 disabled 变 enabled
3. 点击合成：`page.locator('button.btn-primary').click()`
4. 等待完成（比 sleep 可靠）：等待 `.down-block audio` 的 `src` 非空，或 `.down-block button` 变 enabled
5. 下载：优先读 `audio.src` 直接用 `page.request.get()` 保存；若无直链再用 `expect_download`
6. 登录态：用 `launch_persistent_context` 复用用户目录，避免每次重新登录
7. 弹窗均非原生 dialog，直接用 `div` 文本/class 点击，不要等 `role=dialog`

## 七、脚本实测补充（2026-11-08，Playwright）

- **免登录**：匿名即可合成，登录弹窗不会自动出现
- **无头模式不可用**：headless Chromium 会被 Cloudflare 挑战/降速（61 字 7 分钟不完成），改用可见窗口 + 真实 UA + `--disable-blink-features=AutomationControlled` 后 9–70 秒完成
- **按钮时序**：`fill` 后按钮不是立刻可用，需等待 `disabled=false`；点击后先变 `disabled`（文案先清空、随后显示 `0%` 进度），生成完成才恢复 `文本合成语音`
- **完成断言**：按钮 `disabled → enabled` 成立，同时 `.down-block audio` 的 `src` 从空变为 `blob:`、下载按钮由 `disabled` 变为可点
- **下载方式**：实测点击 `.down-block button` 会触发真实 download 事件，`expect_download` + `save_as` 可直接落盘（保留 blob fetch 兜底）
- **耗时**：同样 61 字文本实测 9s / 63s 波动较大，批量脚本默认单行超时 180s
