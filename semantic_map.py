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
import html as html_mod
import math
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

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


def load_from_sitemap(url: str) -> list:
    with urllib.request.urlopen(url, timeout=30) as r:
        sm = r.read().decode("utf-8", errors="ignore")
    locs = re.findall(r"<loc>\s*(.*?)\s*</loc>", sm)
    pages = []
    for loc in locs:
        try:
            with urllib.request.urlopen(loc, timeout=30) as r:
                text = strip_html(r.read().decode("utf-8", errors="ignore"))
            if len(text) > 200:
                pages.append((loc, text))
            print(f"  fetched {loc}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001 — 單頁失敗不該毀掉整張地圖
            print(f"  skip {loc}: {e}", file=sys.stderr)
    return pages


def main() -> int:
    ap = argparse.ArgumentParser(description="網站語意地圖:撞稿與孤島偵測")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--dir", help="本機 HTML 資料夾")
    src.add_argument("--sitemap", help="sitemap.xml 網址")
    ap.add_argument("--cannibal", type=float, default=CANNIBAL_T)
    ap.add_argument("--close", type=float, default=CLOSE_T)
    ap.add_argument("--out", help="輸出 Markdown 報告路徑(省略則印到終端)")
    args = ap.parse_args()

    pages = load_from_dir(Path(args.dir)) if args.dir else load_from_sitemap(args.sitemap)
    if len(pages) < 2:
        print("頁數不足(<2),沒東西可比。", file=sys.stderr)
        return 1

    names = [n for n, _ in pages]
    vecs = tfidf_vectors([tokenize(t) for _, t in pages])

    pairs = []
    max_sim = [0.0] * len(pages)
    for i in range(len(pages)):
        for j in range(i + 1, len(pages)):
            s = cos(vecs[i], vecs[j])
            max_sim[i] = max(max_sim[i], s)
            max_sim[j] = max(max_sim[j], s)
            if s >= args.close:
                pairs.append((s, names[i], names[j]))
    pairs.sort(reverse=True)
    islands = sorted((max_sim[i], names[i]) for i in range(len(pages)) if max_sim[i] < ISLAND_T)

    lines = [f"# 語意地圖報告({len(pages)} 頁)", ""]
    lines.append(f"## 撞稿候選(相似度 >= {args.cannibal})")
    hit = [p for p in pairs if p[0] >= args.cannibal]
    lines += [f"- **{s:.3f}**  {a}  ↔  {b}" for s, a, b in hit] or ["- 無 ✅"]
    lines += ["", f"## 太接近(>= {args.close},新文換角度)"]
    near = [p for p in pairs if p[0] < args.cannibal]
    lines += [f"- {s:.3f}  {a}  ↔  {b}" for s, a, b in near] or ["- 無 ✅"]
    lines += ["", f"## 孤島頁(全站最大相似度 < {ISLAND_T},缺內鏈脈絡)"]
    lines += [f"- {s:.3f}  {n}" for s, n in islands] or ["- 無 ✅"]
    lines += ["", "> 閾值是經驗值非鐵律:撞稿候選請人工複核搜尋意圖是否真的相同;",
              "> 兩頁服務不同意圖(教學 vs 比較)即使相似也可共存。"]

    report = "\n".join(lines)
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"報告已寫入 {args.out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
