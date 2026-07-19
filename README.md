# article-overlap-checker — 文章撞稿檢查

> Find articles competing for the same ranking (keyword cannibalization) and orphan pages with no internal-link context. Pure Python stdlib, zero dependencies, CJK-aware.

掃你的網站(HTML 資料夾或 sitemap),用 TF-IDF 相似度回報三件事:

1. **撞稿候選** — 兩頁太像,搜尋引擎可能分不清誰該排名(keyword cannibalization)
2. **太接近** — 新文章選題的預警線
3. **孤島頁** — 跟全站都不像、缺內鏈脈絡的頁面

純 Python 標準庫、零依賴、中英混排通吃(CJK 字元 bigram)。0.33 秒掃 50 頁。

## 使用

```bash
# 本機 HTML 資料夾(建議掃整個站的輸出目錄,只掃子資料夾會高估孤島)
python semantic_map.py --dir <網站輸出資料夾> --out report.md

# 或直接掃線上 sitemap(會逐頁下載,頁多時較慢)
python semantic_map.py --sitemap https://example.com/sitemap.xml --out report.md
```

也可以當 Claude Code plugin 用(裝了之後直接用講的,AI 會跑工具幫你讀報告):

```
/plugin marketplace add Coolkidlab-Yin/Coolkidlab
/plugin install article-overlap-checker@coolkidlab
```

## 讀報告的原則

1. **閾值是經驗值不是鐵律**:預設 0.62/0.55 在一個 75 頁繁中站校準;第一次跑先看分布,再用 `--cannibal`/`--close` 調。
2. **撞稿候選要人工複核搜尋意圖**:兩頁服務不同意圖(教學 vs 比較 vs 故障排除)即使相似度高也可以共存;真撞稿是「同一個搜尋意圖有兩個入口」。
3. **孤島頁的解法是內鏈不是刪除**:先補相關文章互連,再觀察。
4. 新文章寫完重跑一次,確認沒有製造新的撞稿(寫作流程的最後一道檢查)。

## 侷限(誠實告知)

- TF-IDF 是詞面相似,抓得到「用詞重疊」抓不到「換句話說的同義」;分數異常低但你直覺很像的頁面,請用人工判斷推翻工具。
- 需要頁面正文 > 200 字才納入(太短的頁面沒有統計意義)。
- 設計對象是網站文章;社群短貼文(Threads/X 這類)詞太少,分數會普遍偏低(實測一批短文案中位數僅 0.016),只能當粗篩,意圖重不重疊要人工判讀。

## 實戰背景

這工具在我自己的 75 頁網站上抓出過真實撞稿(兩篇比較文相似度 0.744),也診斷出整個站的主題漂移 — 完整故事在 [連載 #25:帶最多流量的頁反而在拖累你想排的詞](https://www.coolkidlab.com/seo-journey/semantic-map-topic-drift.html)。更多 build-in-public 記錄在 [coolkidlab.com](https://www.coolkidlab.com)。

> 2026-07-18 更名:原名 semantic-map,為了讓人一看就知道用途改為 article-overlap-checker。

## Credits

撞稿、主題漂移、語意集中度這些**觀念**,啟發自 [@darkseoking](https://www.threads.com/@darkseoking) 的 SEO 教學內容 — 值得追蹤的繁中 SEO 創作者。本工具的**實作**(演算法選擇、閾值校準、CJK 處理)是 Coolkid AI Lab 在自己站台上實測的產物。觀念是公共的,實作是自己的,數據是站台的 — 三層分開標,是這個 Lab 的誠實原則。

## License

MIT
