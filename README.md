# Carbon-Aware Procurement MVP (Local + OpenAI API)

## 功能

1. **PDF OCR**：使用 Tesseract 將報價/EPD PDF 轉為表格  
2. **OpenAI 估碳**：缺少 GWP 時，透過 GPT-4o 估算碳因子  
3. **多目標優化**：`pymoo` NSGA-II 同步最小化成本 / 碳 / 交期（未完成）  
4. **議價稿生成**：GPT 生成對供應商的談判話術（未完成）  
5. **Dashboard**：Streamlit 端到端操作  

---

## 環境安裝

```bash
# 安裝系統相依元件（Windows 已有 Tesseract 可跳過）
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

choco install tesseract

# Python 環境
cd 檔案位置
pip install -r requirements.txt

# 虛擬機 Python 環境
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

---

## 環境變數

- 下載 [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/)
- 將 Poppler 的 `bin` 目錄（如：`C:\poppler-xx.x.x\bin`）加入 PATH

建立 `.env` 或於 shell export：

```
OPENAI_API_KEY="sk-..."
OPENAI_MODEL="gpt-4o-mini"
```

---

## 執行

```bash
# 各開一個 cmd 或 powershell 執行
uvicorn app.main:app --reload --port 8000
streamlit run dashboard/app.py

# 我的習慣：
# 虛擬機開 uvicorn app.main:app --reload --port 8000
# 本機端開 streamlit run dashboard/app.py
# 備註：相反應該也沒差（不確定）
```

---

## 結構

```
app/
  main.py            # FastAPI 入口
dashboard/
  app.py             # Streamlit 前端
modules/
  ocr.py
  optimizer.py
  openai_helper.py
requirements.txt
```

---

## 注意事項

- 若前端上傳 PDF 報錯 "AxiosError: Request failed with status code 400"，請將 PDF 檔名改為英文。

