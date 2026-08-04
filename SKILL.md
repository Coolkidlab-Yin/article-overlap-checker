---
name: article-overlap-checker
description: >
  掃描本機 HTML 網站輸出或單層 sitemap，找出可能互搶排名的相似文章、選題過近頁面與
  詞面孤島頁，並產出可人工複核的 Markdown 報告。當使用者要檢查 keyword
  cannibalization、內容重複、既有文章是否撞題、新文章選題距離或全站內容脈絡時使用；
  輸入為一個 HTML 根目錄或 sitemap.xml URL，輸出為相似度分布、候選配對與孤島清單。
---

# 文章撞稿檢查

## 引導邊界

腳本只負責可重現的文字相似度與分布；執行 Agent 依網站目的、GSC 證據與內容
語境補完判讀。不要為了覆蓋所有 SEO 情境擴張腳本，也不要把預設閾值當通用定律。

## 適用與不適用

適用：比較同一網站的長篇內容、在寫新文章前做撞題預警、找出需補內鏈脈絡的頁面。

不適用：

- 判定搜尋引擎已經發生 cannibalization；請再用 GSC 查詢與排名資料驗證。
- 比較社群短文、圖片或影片；正文太短時 TF-IDF 分數沒有足夠訊號。
- 偵測改寫後的同義內容、法律意義上的抄襲或跨語言語意重複。
- 自動決定合併、刪除或重新導向頁面；這些動作需人工確認搜尋意圖與流量。

## 開始前輸入

先取得：

1. **來源二選一**：完整網站建置輸出的 HTML 根目錄，或可公開開啟的單層 `sitemap.xml` URL。
2. **報告路徑**：例如 `reports/overlap.md`；不要覆蓋使用者仍需保留的檔案。
3. **可選閾值**：先用預設值；若要調整，必須符合 `0 <= close <= cannibal <= 1`。
4. **分析目的**：全站盤點、特定新文撞題，或內鏈盤點；目的會影響人工複核方式。

只掃子目錄會高估孤島。sitemap index 或巢狀 sitemap 不在本腳本支援範圍；改傳子
sitemap，或優先掃本機完整輸出。

## 執行模式

有檔案系統與網路能力時，agent 直接定位並執行腳本、讀取報告、回傳結論；不要把可代跑
的命令丟回給使用者。只有缺少本機路徑、網路受限或需要使用者選擇報告覆寫位置時才停下來。

腳本純 Python 標準庫，不需安裝套件。不要假設目前目錄有 `scripts/`：plugin 安裝版優先
從 `${CLAUDE_PLUGIN_ROOT}` 定位，裸 repo 才使用根目錄的 `semantic_map.py`。

### 定位腳本並先看說明

macOS / Linux / Git Bash：

```bash
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/skills/article-overlap-checker/scripts/semantic_map.py" ]; then
  SCRIPT="${CLAUDE_PLUGIN_ROOT}/skills/article-overlap-checker/scripts/semantic_map.py"
elif [ -f "./semantic_map.py" ]; then
  SCRIPT="./semantic_map.py"
elif [ -f "./scripts/semantic_map.py" ]; then
  SCRIPT="./scripts/semantic_map.py"
else
  echo "找不到 semantic_map.py" >&2; exit 1
fi
python "$SCRIPT" --help
```

PowerShell：

```powershell
$scriptPath = $null
if ($env:CLAUDE_PLUGIN_ROOT) {
  $candidate = Join-Path $env:CLAUDE_PLUGIN_ROOT 'skills\article-overlap-checker\scripts\semantic_map.py'
  if (Test-Path -LiteralPath $candidate) { $scriptPath = $candidate }
}
if (-not $scriptPath -and (Test-Path -LiteralPath '.\semantic_map.py')) { $scriptPath = '.\semantic_map.py' }
if (-not $scriptPath -and (Test-Path -LiteralPath '.\scripts\semantic_map.py')) { $scriptPath = '.\scripts\semantic_map.py' }
if (-not $scriptPath) { throw '找不到 semantic_map.py' }
python $scriptPath --help
```

通過判準：`--help` 顯示互斥的 `--dir`、`--sitemap`，以及 `--cannibal`、`--close`、
`--out`。若 `python` 不存在，改用環境既有的 `python3` 或 `py -3`，不要安裝未知執行檔。
目前腳本的 `--cannibal` help 有一句「要低於 `--close`」是既有文案誤植；依實際分類邏輯，
有效關係是 `--close <= --cannibal`。本 Skill 的驗收以實際腳本邏輯為準。

## 工作流程

| 步驟 | 動作 | 為什麼 | 通過判準 |
|---|---|---|---|
| 1. 驗證輸入 | 確認只提供 `--dir` 或 `--sitemap` 其中一個；檢查路徑存在或 URL 回傳 sitemap XML | 避免把打錯路徑誤判成網站沒內容 | 本機根目錄可讀，或 sitemap 有 `<loc>` 且不是 sitemap index |
| 2. 建立基準報告 | 先用預設閾值執行並保留 stdout、stderr | 預設值是起點，先看站內實際分布再校準 | exit code 0、終端顯示 `報告已寫入`、檔案可讀 |
| 3. 檢查完整性 | 比對報告頁數、sitemap `<loc>` 數與 stderr 的 `fetched` / `skip` | 部分抓取若被誤當成功，結論會失真 | 至少 2 頁；失敗頁少於一半；沒有 exit code 3 或 sitemap-index 錯誤 |
| 4. 讀分布再調閾值 | 先讀「相似度分布」，必要時同時調整 `--close` 與 `--cannibal` 重跑 | 各站詞彙密度不同，固定閾值不是證據 | `close <= cannibal`，候選量足以人工檢查且不是靠任意單一分數定案 |
| 5. 人工複核意圖 | 對每組高分頁標記「同意圖／不同意圖／不確定」 | 詞面相似不等於搜尋意圖相同 | 每個撞稿候選都有理由與建議，不以分數直接刪頁 |
| 6. 解讀孤島 | 把孤島視為「詞面脈絡弱」提示，檢查導覽、內鏈與主題歸屬 | 工具沒有讀取實際連結圖，不能證明它沒有內鏈 | 每頁都有「補內鏈／保留／人工再查」處置，而非自動刪除 |

### 執行命令

本機 HTML：

```bash
SITE_ROOT="/path/to/site-output"
REPORT_PATH="./report.md"
python "$SCRIPT" --dir "$SITE_ROOT" --out "$REPORT_PATH"
```

PowerShell 使用前段取得的 `$scriptPath`：

```powershell
python $scriptPath --dir '<網站輸出根目錄>' --out '<報告.md>'
```

單層 sitemap：

```bash
python "$SCRIPT" --sitemap https://example.com/sitemap.xml --out report.md
```

校準範例（只在讀過基準分布後使用）：

```bash
python "$SCRIPT" --dir "$SITE_ROOT" --close 0.50 --cannibal 0.60 --out report-calibrated.md
```

## 輸出解讀

- **撞稿候選**：相似度達 `--cannibal`；只代表優先人工複核，不是排名衝突證據。
- **太接近**：介於 `--close` 與 `--cannibal`；用於新文換角度或補差異化。
- **相似度分布**：全站最高配對；用它判斷門檻是否脫離本站分布。
- **孤島頁**：與其他頁的最大詞面相似度低於工具固定門檻；它不是實際內鏈爬蟲結果。

真正撞稿是「同一搜尋意圖有兩個入口」。教學、比較、案例與故障排除即使用詞相似，也可能
應該共存。孤島優先補相關內鏈與脈絡，不要因單次報告直接刪除。

## 停止條件與排錯

- `找不到資料夾` 或 exit code 2：修正來源路徑，不要建立空報告充數。
- `頁數不足(<2)` 或 exit code 1：確認掃到建置根目錄，且至少兩頁正文超過 200 字。
- exit code 3：sitemap index 或至少一半頁面抓取失敗；工具不會寫報告，先修正來源再重跑。
- `抓不到 sitemap` / 沒有 `<loc>`：用瀏覽器或 HTTP 工具驗證網址；被擋時改掃本機。
- 出現 sitemap index 警告：停止解讀，改用其中一個子 sitemap 或本機輸出。
- `skip` 達 `<loc>` 的一半以上：報告視為殘缺，停止下任何全站結論。
- 最高分遠低於預設門檻：同時下調 `--close` 與 `--cannibal` 後重跑；保留兩份報告供比較。
- 編碼異常：先確認 HTML 真的是可解碼文字；腳本會忽略無法解碼字元，可能使分數偏低。

## 完成定義

只有同時符合以下條件才回報完成：

- 報告檔存在，首行為 `# 語意地圖報告(N 頁)`，且 `N >= 2`。
- 沒有達停止條件的殘缺抓取；若有少量 skip，明列數量與受影響 URL。
- 已讀相似度分布，並交代閾值是預設或校準值。
- 每個撞稿候選已人工複核搜尋意圖；孤島已標成脈絡提示而非事實判決。
- 回傳報告絕對路徑、來源範圍、頁數、候選數、孤島數與下一步。

## 安全與侷限

- 只讀來源 HTML 與公開 URL；不要修改、刪除或發布網站內容。
- 不把登入後頁面、個資、內部草稿或 token 傳給第三方；sitemap 模式只用公開 URL。
- sitemap 模式只允許公開 HTTPS、443 port、同來源頁面；redirect 也會重驗，連線固定到
  驗證過的公開 IP 並保留原網域的 TLS 驗證；拒絕 private／loopback／link-local／reserved
  位址、不符 MIME 與過大回應。大型站仍應先取得授權，
  並注意對方負載與使用條款。
- TF-IDF + cosine 是詞面模型；CJK 使用字元 bigram，抓不到同義改寫與跨語言語意。
- 200 字以下頁面不納入。預設 0.62 / 0.55 是作者在 75 頁繁中站的經驗校準，不具普遍性。

## 來源與時效

截至 **2026-08-02** 查證：

- Coolkidlab plugin 根 README：https://github.com/Coolkidlab-Yin/Coolkidlab
- 獨立 repo README：https://github.com/Coolkidlab-Yin/article-overlap-checker
- 執行行為以同目錄 `scripts/semantic_map.py` 的 `--help` 與 exit code 為準。
- Sitemap 協定（官方規格）：https://www.sitemaps.org/protocol.html
