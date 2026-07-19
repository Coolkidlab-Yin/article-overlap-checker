# 範例輸出:實際掃描 coolkidlab.com(123 頁,2026-07-19)

> 以下內容為 `semantic_map.py --dir <建置輸出資料夾>` 的實跑輸出(未改任何數字),
> 站點為繁中/英文混排的 AI 教學站,123 頁掃完約 1.4 秒(純標準庫、無第三方依賴)。
> 註:掃描前先排除了建置目錄內殘留的一份舊站副本——完全相同的重複頁會以 **1.000** 滿分
> 洗版撞稿區,如果你的報告開頭出現大量 1.000,先檢查是不是掃到建置殘留/備份副本。

---

# 語意地圖報告(123 頁)

## 撞稿候選(相似度 >= 0.62)
- **0.803**  seo-journey\from-seo-to-geo.apple.html  ↔  seo-journey\from-seo-to-geo.html
- **0.733**  newbie-pitfalls\ai-agent-vs-chatgpt.html  ↔  newbie-pitfalls\claude-code-vs-chatgpt.html

## 太接近(>= 0.55,新文換角度)
- 無 ✅

## 孤島頁(全站最大相似度 < 0.15,缺內鏈脈絡)
- 0.042  404.html
- 0.044  build-log\index.html
- 0.049  drafts\mockup-hero\index.html
- 0.067  newbie-pitfalls\claude-code-screenshot-workflow.html
- 0.073  newbie-pitfalls\claude-code-github-app.html
- 0.076  about.html
- 0.082  newbie-pitfalls\claude-code-telegram-remote.html
- 0.097  workflows\market-scanner.html
- 0.098  newbie-pitfalls\what-is-seo-personal-site.html
- 0.100  seo-journey\semantic-map-topic-drift.html

(節錄:完整清單共 30 頁,其餘 20 頁分數介於 0.104〜0.150,省略)

> 閾值是經驗值非鐵律:撞稿候選請人工複核搜尋意圖是否真的相同;
> 兩頁服務不同意圖(教學 vs 比較)即使相似也可共存。

---

## 怎麼讀這份報告(掃描當事人的實際判讀)

- **0.803 那對**:`*.apple.html` 是同一篇文章的裝置別變體 → 真陽性,
  該用 canonical 或從 sitemap 移除變體,而不是改寫內容。
- **0.733 那對**:「AI Agent vs ChatGPT」和「Claude Code vs ChatGPT」是兩個不同
  搜尋意圖的比較文 → 撞稿候選需人工複核的典型例子,結論是可共存,但值得互加內鏈。
- **孤島頁**:404、聯絡頁、法務頁本來就孤島,可忽略;真正該處理的是像
  `market-scanner.html` 這種主題文章孤島 → 補內鏈、或在選題地圖上補橋接文。
