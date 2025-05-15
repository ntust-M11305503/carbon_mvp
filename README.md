
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
sudo apt-get update && sudo apt-get install -y poppler-utils tesseract-ocr

# Python 環境
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

## 環境變數
建 `.env` 或在 shell export  
```
OPENAI_API_KEY=sk-...
MODEL=gpt-4o-mini
DATA_DIR=data
```

## 執行
```bash
uvicorn app.main:app --reload
streamlit run dashboard/app.py
```

## 結構
```
app/
  main.py          # FastAPI 入口
modules/
  ocr.py
  optimizer.py
  openai_helper.py
dashboard/
  app.py           # Streamlit 前端
requirements.txt
```

## Note
- OCR 正則僅為示範，實務需依表格樣式調整  
- `pymoo` 已內嵌 NSGA-II；人口 & 代數可於 `optimizer.optimize_materials` 調整  
- OpenAI 費用：估碳&議價段落 token 每次上百字，成本極低
