#!/usr/bin/env python3
"""semantic-map — 網站語意地圖:撞稿(cannibalization)與孤島頁偵測。

用 TF-IDF + cosine 相似度掃一個資料夾(或 sitemap)裡的 HTML 頁面,回報:
  1. 撞稿候選:兩頁相似度 >= CANNIBAL 閾值 → 搜尋引擎可能分不清誰該排名
  2. 太接近:介於 CLOSE~CANNIBAL 之間 → 新文選題時建議換角度
  3. 孤島頁:跟全站任何頁都不像 → 缺內鏈脈絡,AI/搜尋引擎難定位它

用法:
  python semantic_map.py --dir ./public                 # 掃本機 HTML 資料夾
  python semantic_map.py --sitemap https://example.com/sitemap.xml
  python semantic_map.py --dir ./public --out report.md

閾值預設 0.62 / 0.55,是在一個 75 頁繁中站上實測校準的經驗值 —
你的站請跑一次後看分布再調(--cannibal 0.7 --close 0.6)。

純標準庫,無第三方依賴。CJK 用字元 bigram、英數用單字 token,
中英混排的站(台灣站常態)都吃得動。
"""
import argparse
import heapq
import html as html_mod
import math
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

# 不帶 UA 的 urllib 預設會送 "Python-urllib/3.x",掛 CDN 的站(Cloudflare 等)直接回 403。
USER_AGENT = "Mozilla/5.0 (compatible; article-overlap-checker/1.0; +https://github.com/Coolkidlab-Yin/article-overlap-checker)"

TOP_N = 10  # 報告固定列出的最高分配對數量(不受閾值影響,用來判斷閾值調得對不對)

CANNIBAL_T = 0.62  # >= 此值:撞稿候選(經驗閾值,供排序與人工複核,非鐵律)
CLOSE_T = 0.55     # >= 此值:太接近,新文建議換角度
ISLAND_T = 0.15    # 全站最大相似度 < 此值:孤島頁


def strip_html(raw: str) -> str:
    """HTML → 純文字。去 script/style/nav/footer 後拔標籤。"""
    raw = re.sub(r"<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html_mod.unescape(raw)).strip()


def tokenize(text: str) -> list:
    """CJK 字元 bigram + 英數單字。中英混排通吃,不需要斷詞器。"""
    tokens = [w.lower() for w in re.findall(r"[A-Za-z0-9]{2,}", text)]
    cjk = re.findall(r"[一-鿿㐀-䶿]", text)
    tokens += ["".join(p) for p in zip(cjk, cjk[1:])]
    return tokens


def tfidf_vectors(docs: list) -> list:
    """list[list[token]] → list[dict[token, weight]](L2 正規化)。"""
    n = len(docs)
    df = Counter()
    for toks in docs:
        df.update(set(toks))
    vecs = []
    for toks in docs:
        tf = Counter(toks)
        total = max(1, len(toks))
        v = {t: (c / total) * math.log((n + 1) / (df[t] + 1)) for t, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecs.append({t: x / norm for t, x in v.items()})
    return vecs


def cos(a: dict, b: dict) -> float:
    if len(b) < len(a):
        a, b = b, a
    return sum(x * b.get(t, 0.0) for t, x in a.items())


def load_from_dir(root: Path) -> list:
    pages = []
    for p in sorted(root.rglob("*.html")):
        text = strip_html(p.read_text(encoding="utf-8", errors="ignore"))
        if len(text) > 200:  # 太短的頁(轉址殼、空模板)不進地圖
            pages.append((str(p.relative_to(root)), text))
    return pages


def fetch(url: str, timeout: int = 30) -> str:
    """帶 UA 抓一頁。少了 UA,掛 CDN 的站會回 403(含本工具作者自己的站)。"""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="ignore")


def load_from_sitemap(url: str) -> list:
    try:
        sm = fetch(url)
    except Exception as e:  # noqa: BLE001 — 抓不到 sitemap 是使用者輸入問題,不該吐 traceback
        print(
            f"抓不到 sitemap:{url}\n  {e}\n"
            f"  檢查:網址對不對(先用瀏覽器開開看)、對方站有沒有掛 sitemap、"
            f"是不是被擋。掃本機建置輸出可以改用 --dir。",
            file=sys.stderr,
        )
        return []
    locs = re.findall(r"<loc>\s*(.*?)\s*</loc>", sm)
    if not locs:
        print(
            f"這個網址抓得到,但裡面沒有任何 <loc> 條目:{url}\n"
            f"  它可能不是 sitemap(貼到首頁了?)、或是回了一頁錯誤頁。"
            f"先用瀏覽器開開看,內容應該是一堆 <url><loc>...</loc></url>。",
            file=sys.stderr,
        )
        return []
    if any(loc.rstrip().endswith((".xml", ".xml.gz")) for loc in locs):
        print(
            "  注意:這份 sitemap 裡有指向其他 .xml 的條目(sitemap index)。"
            "本工具只吃單層 sitemap,巢狀的子 sitemap 會被當成網頁抓而失敗 —— "
            "請改用子 sitemap 的網址,或用 --dir 掃本機建置輸出。",
            file=sys.stderr,
        )
    pages, failed = [], 0
    for loc in locs:
        try:
            text = strip_html(fetch(loc))
            if len(text) > 200:
                pages.append((loc, text))
            print(f"  fetched {loc}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001 — 單頁失敗不該毀掉整張地圖
            failed += 1
            print(f"  skip {loc}: {e}", file=sys.stderr)
    # 大部分頁面掛掉時,報告只涵蓋殘存的少數頁,結論會失真。靜默成功比失敗更糟。
    if failed and failed >= len(locs) / 2:
        print(
            f"\n⚠ {len(locs)} 頁裡有 {failed} 頁抓失敗,這份報告只涵蓋 {len(pages)} 頁,"
            f"不足以下結論。\n  先處理抓取問題(對方擋、逾時、網址失效)再重跑。",
            file=sys.stderr,
        )
    return pages


def main() -> int:
    ap = argparse.ArgumentParser(description="網站語意地圖:撞稿與孤島偵測")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--dir", help="本機 HTML 資料夾")
    src.add_argument("--sitemap", help="sitemap.xml 網址")
    ap.add_argument(
        "--cannibal", type=float, default=CANNIBAL_T,
        help=f"撞稿候選的相似度門檻(預設 {CANNIBAL_T})。調低會列出更多候選。"
             f"注意:要低於 --close 才看得到,兩個都要一起調",
    )
    ap.add_argument(
        "--close", type=float, default=CLOSE_T,
        help=f"「太接近」的相似度門檻(預設 {CLOSE_T}),也是報告收錄配對的下限。"
             f"想看更低分的配對就調低這個",
    )
    ap.add_argument("--out", help="輸出 Markdown 報告路徑(省略則印到終端)")
    args = ap.parse_args()

    if args.dir:
        root = Path(args.dir)
        # 路徑打錯跟「站上真的沒東西」是兩件事,分開講,不然使用者會誤判自己的站空了。
        if not root.is_dir():
            print(f"找不到資料夾:{root}", file=sys.stderr)
            return 2
        pages = load_from_dir(root)
    else:
        pages = load_from_sitemap(args.sitemap)
    if len(pages) < 2:
        hint = (
            "是不是掃錯層(要指到建置輸出的根目錄)、或頁面正文都不到 200 字"
            if args.dir
            else "看上面的訊息:sitemap 本身抓不到、裡面沒有 <loc> 條目、"
            "或頁面都抓失敗(會有 skip 那幾行)"
        )
        print(
            f"頁數不足(<2),沒東西可比。\n  掃到 {len(pages)} 頁。檢查:{hint}。",
            file=sys.stderr,
        )
        return 1

    names = [n for n, _ in pages]
    vecs = tfidf_vectors([tokenize(t) for _, t in pages])

    pairs = []
    top = []  # 不受閾值影響的全站最高分配對,避免「無 ✅」被誤讀成「真的沒問題」
    max_sim = [0.0] * len(pages)
    for i in range(len(pages)):
        for j in range(i + 1, len(pages)):
            s = cos(vecs[i], vecs[j])
            max_sim[i] = max(max_sim[i], s)
            max_sim[j] = max(max_sim[j], s)
            if s >= args.close:
                pairs.append((s, names[i], names[j]))
            item = (s, names[i], names[j])
            if len(top) < TOP_N:
                heapq.heappush(top, item)
            elif s > top[0][0]:
                heapq.heapreplace(top, item)
    pairs.sort(reverse=True)
    top.sort(reverse=True)
    islands = sorted((max_sim[i], names[i]) for i in range(len(pages)) if max_sim[i] < ISLAND_T)

    lines = [f"# 語意地圖報告({len(pages)} 頁)", ""]
    lines.append(f"## 撞稿候選(相似度 >= {args.cannibal})")
    hit = [p for p in pairs if p[0] >= args.cannibal]
    lines += [f"- **{s:.3f}**  {a}  ↔  {b}" for s, a, b in hit] or [
        f"- 無 —— 沒有任何一組配對達到 {args.cannibal}。"
        f"**先看下面的「相似度分布」再下結論**:如果最高分離門檻很遠,"
        f"代表這個站的用詞本來就分散,門檻該往下調,不是真的沒撞稿。"
    ]
    lines += ["", f"## 太接近(>= {args.close},新文換角度)"]
    near = [p for p in pairs if p[0] < args.cannibal]
    lines += [f"- {s:.3f}  {a}  ↔  {b}" for s, a, b in near] or ["- 無"]
    lines += ["", f"## 相似度分布(全站最高的 {len(top)} 組,不受閾值影響)", ""]
    lines += [
        "先看這一段再看上面兩段。這裡列的是全站相似度最高的配對,不管門檻設多少都會列 —— "
        "用它判斷你的門檻設得對不對。",
        "",
    ]
    lines += [
        f"- {s:.3f}  {a}  ↔  {b}" + ("   ← 目前門檻在這附近" if abs(s - args.cannibal) < 0.03 else "")
        for s, a, b in top
    ]
    if top:
        lines += [
            "",
            f"> 全站最高分 **{top[0][0]:.3f}**,目前撞稿門檻 {args.cannibal}。"
            + (
                "最高分低於門檻,調整建議:把 `--close` 和 `--cannibal` **一起**往下調"
                "(只調 `--cannibal` 沒用,報告只收錄 >= `--close` 的配對),"
                f"例如 `--close {max(top[0][0] - 0.15, 0.05):.2f} --cannibal {max(top[0][0] - 0.05, 0.1):.2f}`。"
                if top[0][0] < args.cannibal
                else "門檻位置合理。"
            ),
        ]
    lines += ["", f"## 孤島頁(全站最大相似度 < {ISLAND_T},缺內鏈脈絡)"]
    lines += [f"- {s:.3f}  {n}" for s, n in islands] or ["- 無 ✅"]
    lines += ["", "> 閾值是經驗值非鐵律:撞稿候選請人工複核搜尋意圖是否真的相同;",
              "> 兩頁服務不同意圖(教學 vs 比較)即使相似也可共存。"]

    report = "\n".join(lines)
    if args.out:
        out = Path(args.out)
        if out.parent and not out.parent.exists():
            out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"報告已寫入 {args.out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
