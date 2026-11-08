# -*- coding: utf-8 -*-
"""批量 TTS：读取 Excel，逐行操作 https://ai-speaker.net/zh 合成语音并下载。

运行：
    C:\\Users\\admin\\.conda\\envs\\py311\\python.exe d:\\work\\ai_brower\\tts_batch.py
    可选参数见 --help
"""

import argparse
import base64
import re
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

import openpyxl
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

TARGET_URL = "https://ai-speaker.net/zh"
TEXTAREA_SEL = 'textarea[placeholder="输入要合成文本"]'
BUTTON_SEL = "button.btn-primary"
DOWN_BLOCK_SEL = ".down-block"
AUDIO_SEL = ".down-block audio"
DOWNLOAD_BTN_SEL = ".down-block button"

HEADER_WORDS = {"语音名称", "名称", "文件名", "语音", "文字", "文本", "内容", "保存路径", "路径", "目录"}
INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\r\n\t]')
RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}

# Playwright 默认单步超时（毫秒）
STEP_TIMEOUT_MS = 30_000


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def sanitize_name(raw: str) -> str:
    """清理 Windows 非法字符，去掉首尾空白与结尾的点。"""
    name = INVALID_FILENAME_CHARS.sub("_", str(raw)).strip()
    name = name.strip(" .")
    if not name:
        name = "unnamed"
    if name.upper() in RESERVED_NAMES:
        name = f"_{name}"
    return name[:80]


def looks_like_header(cells: list) -> bool:
    """自动判断第一行是否为表头：名称列命中表头词，或保存路径列不像路径。"""
    first = str(cells[0] or "").strip()
    third = str(cells[2] or "").strip()
    if first.replace(" ", "") in HEADER_WORDS:
        return True
    path_like = bool(re.match(r"^[A-Za-z]:[\\/]", third)) or ("\\" in third) or ("/" in third)
    return not path_like


def read_rows(excel_path: Path, header_mode: str, limit: int | None) -> list[tuple[str, str, str]]:
    """返回 [(语音名称, 文本, 保存目录)]，跳过表头/空行。header_mode: auto|yes|no"""
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    ws = wb.active
    raw_rows = [list(r) for r in ws.iter_rows(max_col=3, values_only=True)]
    raw_rows = [r + [None] * (3 - len(r)) for r in raw_rows]

    data_rows = raw_rows
    if header_mode == "yes" or (header_mode == "auto" and raw_rows and looks_like_header(raw_rows[0])):
        data_rows = raw_rows[1:]
        if header_mode == "auto":
            log(f"检测到表头，已跳过第 1 行：{raw_rows[0]}")

    result = []
    for row in data_rows:
        name, text, directory = (str(c or "").strip() for c in row[:3])
        if not (name or text or directory):
            continue  # 完全空行
        if not name or not text or not directory:
            log(f"跳过不完整行（缺列）：{row[:3]}")
            continue
        if len(text) > 5000:
            log(f"跳过 {name}：文本 {len(text)} 字，超过页面 5000 字上限")
            continue
        result.append((name, text, directory))
        if limit and len(result) >= limit:
            break

    if not result:
        raise RuntimeError("Excel 中没有可处理的数据行（检查表头/空行/列顺序）")
    return result


def unique_target(directory: Path, name: str, overwrite: bool) -> Path:
    """若同名文件存在：overwrite 直接覆盖，否则追加 _1/_2…"""
    target = directory / f"{name}.mp3"
    if overwrite or not target.exists():
        return target
    i = 1
    while True:
        candidate = directory / f"{name}_{i}.mp3"
        if not candidate.exists():
            return candidate
        i += 1


def save_from_blob(page, target: Path) -> None:
    """兜底：从 audio 的 blob URL 直接取字节写盘。"""
    b64 = page.evaluate(
        """async () => {
          const a = document.querySelector('.down-block audio');
          if (!a || !a.src) throw new Error('没有音频地址');
          const resp = await fetch(a.src);
          const buf = await resp.arrayBuffer();
          const bytes = new Uint8Array(buf);
          let binary = '';
          const chunk = 0x8000;
          for (let i = 0; i < bytes.length; i += chunk) {
            binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
          }
          return btoa(binary);
        }"""
    )
    target.write_bytes(base64.b64decode(b64))


def wait_step(page, expr: str, timeout_ms: int, label: str, arg=None) -> None:
    """带阶段名的等待，失败时打印当时页面状态，便于排查。"""
    try:
        page.wait_for_function(expr, arg=arg, timeout=timeout_ms)
    except Exception as e:
        state = page.evaluate(
            """() => {
              const b = document.querySelector('.btn-primary');
              const a = document.querySelector('.down-block audio');
              return {
                title: document.title,
                body: (document.body ? document.body.innerText : '').slice(0, 80),
                btnText: b ? b.textContent.trim() : '',
                btnDisabled: b ? b.disabled : null,
                audioSrc: a ? (a.getAttribute('src') || '').slice(0, 40) : ''
              };
            }"""
        )
        log(f"等待失败[{label}]：{str(e).splitlines()[0]} | 页面状态 {state}")
        raise RuntimeError(f"{label}失败：{str(e).splitlines()[0]}")


def synthesize_one(page, name: str, text: str, target_dir: Path, overwrite: bool, row_timeout: float) -> Path:
    """单行流程：输入 → 合成 → 等按钮恢复可用 → 下载。返回落盘路径。"""
    ta = page.locator(TEXTAREA_SEL)
    wait_step(page, "() => !!document.querySelector('textarea[placeholder=\\'输入要合成文本\\']')", STEP_TIMEOUT_MS, "等待输入框")
    ta.wait_for(state="visible", timeout=STEP_TIMEOUT_MS)
    ta.fill(text)

    # 页面在输入后才启用按钮（并非 fill 后立即可用，需等待）
    wait_step(page, "() => { const b = document.querySelector('.btn-primary'); return b && !b.disabled; }",
              STEP_TIMEOUT_MS, "等待合成按钮启用")

    prev_src = page.evaluate(
        "() => { const a = document.querySelector('.down-block audio'); return a ? (a.getAttribute('src') || '') : ''; }"
    )

    log("点击合成")
    page.locator(BUTTON_SEL).click()
    # 完成信号：按钮先变 disabled，再恢复 enabled（真实行为已验证）
    wait_step(page, "() => { const b = document.querySelector('.btn-primary'); return b && b.disabled === true; }",
              15_000, "等待按钮进入生成中状态")
    wait_step(page, "() => { const b = document.querySelector('.btn-primary'); return b && b.disabled === false; }",
              int(row_timeout * 1000), "等待生成完成")

    # 兜底校验：新音频已生成且下载按钮可用
    wait_step(
        page,
        """(prev) => {
          const a = document.querySelector('.down-block audio');
          const b = document.querySelector('.down-block button');
          return !!(a && a.getAttribute('src') && a.getAttribute('src') !== prev && b && !b.disabled);
        }""",
        STEP_TIMEOUT_MS, "等待音频就绪", arg=prev_src,
    )

    target = unique_target(target_dir, name, overwrite)
    target_dir.mkdir(parents=True, exist_ok=True)

    # 优先 expect_download；页面实际点击下载按钮会触发下载事件
    try:
        with page.expect_download(timeout=STEP_TIMEOUT_MS) as dl_info:
            page.locator(DOWNLOAD_BTN_SEL).click()
        download = dl_info.value
        download.save_as(str(target))
    except Exception as e:
        log(f"未捕获到下载事件（{str(e)[:80]}），改用 audio 直链兜底")
        save_from_blob(page, target)

    if not target.exists() or target.stat().st_size == 0:
        raise RuntimeError("下载结果为空文件")
    return target


def screenshot_on_timeout(page, target_dir: Path, name: str) -> Path | None:
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        shot = target_dir / f"{name}_timeout_{datetime.now():%H%M%S}.png"
        page.screenshot(path=str(shot), full_page=False)
        log(f"超时截图：{shot}")
        return shot
    except Exception as e:
        log(f"截图失败：{e}")
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="批量 TTS：Excel → ai-speaker.net → mp3")
    ap.add_argument("--excel", default=r"D:\work\ai_brower\语音.xlsx", help="Excel 路径")
    ap.add_argument("--header", choices=["auto", "yes", "no"], default="auto", help="首行是否表头")
    ap.add_argument("--timeout", type=float, default=180, help="单行生成超时（秒），默认 180")
    ap.add_argument("--overwrite", action="store_true", help="同名文件直接覆盖（默认加序号）")
    ap.add_argument("--headless", action="store_true", help="无头模式（不建议：实测会被 Cloudflare 挑战降速/卡住）")
    ap.add_argument("--limit", type=int, default=None, help="只处理前 N 行，便于验证")
    args = ap.parse_args()

    excel = Path(args.excel)
    if not excel.exists():
        log(f"Excel 不存在：{excel}")
        return 2

    rows = read_rows(excel, args.header, args.limit)
    log(f"待处理 {len(rows)} 行，单行超时 {args.timeout:.0f}s，浏览器{'无头' if args.headless else '可见窗口'}")

    ok, failed = [], []
    t_start = time.time()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=args.headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(
            accept_downloads=True,
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
            ),
        )
        page = ctx.new_page()
        page.set_default_timeout(STEP_TIMEOUT_MS)
        opened = False
        for attempt in range(1, 4):
            try:
                page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=90_000)
                opened = True
                break
            except Exception as e:
                log(f"打开页面失败（第 {attempt}/3 次）：{str(e).splitlines()[0][:120]}")
                time.sleep(5)
        if not opened:
            log("无法打开目标页面，已终止")
            ctx.close()
            browser.close()
            return 2

        for idx, (name, text, directory) in enumerate(rows, 1):
            target_dir = Path(directory)
            log(f"[{idx}/{len(rows)}] 开始：{name}（{len(text)} 字）-> {target_dir}")
            t0 = time.time()
            last_err: Exception | None = None
            for attempt in range(1, 3):  # 失败重载页面后重试一次
                try:
                    path = synthesize_one(page, name, text, target_dir, args.overwrite, args.timeout)
                    cost = time.time() - t0
                    size = path.stat().st_size
                    ok.append(name)
                    log(f"[{idx}/{len(rows)}] 成功：{path}（{size/1024:.1f} KB，{cost:.1f}s）")
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
                    if attempt == 1:
                        log(f"本行第 1 次失败：{str(e).splitlines()[0][:120]}，重载页面后重试")
                        try:
                            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=90_000)
                        except Exception as e2:
                            log(f"重载页面失败：{str(e2).splitlines()[0][:100]}")

            if last_err is not None:
                cost = time.time() - t0
                reason = f"{str(last_err).splitlines()[0]}"
                failed.append((name, reason[:160]))
                log(f"[{idx}/{len(rows)}] 失败（{cost:.1f}s）：{reason}")
                screenshot_on_timeout(page, target_dir, name)
                log(traceback.format_exc(limit=2))

        ctx.close()
        browser.close()

    total = time.time() - t_start
    log("=" * 56)
    log(f"汇总：总计 {len(rows)}，成功 {len(ok)}，失败 {len(failed)}，总耗时 {total:.1f}s")
    if failed:
        for name, reason in failed:
            log(f"  失败：{name} -> {reason}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
