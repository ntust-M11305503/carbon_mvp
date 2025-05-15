import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from modules import ocr, optimizer, openai_helper
import pandas as pd
from pathlib import Path
from typing import List, Dict

app = FastAPI(title="Carbon Procurement MVP")

# 確保資料夾存在
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(exist_ok=True, parents=True)

@app.post("/upload_pdf")
async def upload_pdf(pdf: UploadFile = File(...)):
    tmp = DATA_DIR / pdf.filename
    with tmp.open("wb") as f:
        f.write(await pdf.read())

    # 正確流程：呼叫 ocr.pdf_to_dataframe 處理 PDF
    try:
        df = ocr.pdf_to_dataframe(tmp)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF 解析失敗：{e}")

    csv_path = tmp.with_suffix(".csv")
    df.to_csv(csv_path, index=False, encoding="utf-8")

    return {
        "csv_path": str(csv_path),
        "rows": len(df),
        "csv_data": df.to_dict(orient="records")
    }

@app.post("/optimize")
async def optimize(data: List[Dict[str, str]]):
    # 檢查資料是否有效
    if not data:
        raise HTTPException(status_code=400, detail="No data received")
    
    # 將傳遞的資料轉換為 DataFrame
    df = pd.DataFrame(data)
    
    # 填寫碳因子
    df = openai_helper.fill_carbon_factors(df)

    # 進行優化
    results = optimizer.optimize_materials(df)
    
    return {"solutions": results}

@app.post("/negotiation_note")
async def note(best_plan: dict):
    # 生成議價稿
    note = openai_helper.generate_negotiation_note(best_plan)
    return {"note": note}
