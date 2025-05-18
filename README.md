
# Carbon-Aware Procurement MVP (Local + OpenAI API)

## 功能
1. **PDF OCR**：使用 Tesseract 把報價/EPD PDF 轉成表格  
2. **OpenAI 估碳**：缺少 GWP 時，透過 GPT-4o 估算碳因子  
3. **多目標優化**：`pymoo` NSGA-II 同步最小化成本 / 碳 / 交期  
4. **議價稿生成**：GPT 生成對供應商的談判話術  
5. **Dashboard**：Streamlit 端到端操作

## 環境安裝
```bash
# 安裝系統相依元件 (Windows 已有 Tesseract 時可跳過)
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

choco install tesseract 

# Python 環境
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

## 環境變數
https://github.com/oschwartz10612/poppler-windows/releases/  下載 Poppler for Windows

將 Poppler 加入 PATH
Poppler 的 bin 目錄。例如：C:\poppler-xx.x.x\bin

建 `.env` 或在 shell export  
```
OPENAI_API_KEY="sk-..."
OPENAI_MODEL="gpt-4o-mini" 
```

## 執行
```bash
# 各開一個 cmd or powershell 來執行
uvicorn app.main:app --reload --port 8000
streamlit run dashboard/app.py
```

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
