import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from modules import ocr, optimizer, openai_helper
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any

app = FastAPI(title="Carbon Procurement MVP")

# 確保資料夾存在
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(exist_ok=True, parents=True)

@app.post("/upload_pdf")
async def upload_pdf(pdf: UploadFile = File(...)):
    tmp = DATA_DIR / pdf.filename
    with tmp.open("wb") as f:
        f.write(await pdf.read())

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

@app.post("/format_table", response_model=None)
async def format_table(raw: Any = Body(...)):
    """
    接收原始 JSON (清單或包含 'csv_data'/'data' 欄位)，統一欄位命名並回傳整理後的表格。
    """
    # 判斷來源
    if isinstance(raw, list):
        records = raw
    elif isinstance(raw, dict) and 'csv_data' in raw and isinstance(raw['csv_data'], list):
        records = raw['csv_data']
    elif isinstance(raw, dict) and 'data' in raw and isinstance(raw['data'], list):
        records = raw['data']
    else:
        raise HTTPException(status_code=400, detail="Invalid JSON format for formatting")

    if not records:
        raise HTTPException(status_code=400, detail="Empty data list")

    df = pd.DataFrame(records)
    # 欄位對應: 中文 -> 英文
    df = df.rename(columns={
        '項次':'item','工程項目':'item','Item':'item',
        '單位':'unit','Unit':'unit',
        '數量':'qty','Quant':'qty',
        '單價':'unit_price','Unit Price':'unit_price',
        '複價':'amount','Amount':'amount'
    })
    # 確保必要欄位存在
    for col in ['item','unit','qty','unit_price','amount']:
        if col not in df.columns:
            df[col] = None
    # 清理數字欄位
    df['qty'] = pd.to_numeric(df['qty'], errors='coerce').fillna(0).astype(int)
    df['unit_price'] = pd.to_numeric(df['unit_price'], errors='coerce').fillna(0).astype(int)
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0).astype(int)

    # 可選保留說明欄
    if '說明' in df.columns:
        df['remark'] = df['說明']

    return {"csv_data": df.to_dict(orient="records")}

@app.post("/optimize", response_model=None)
async def optimize(raw: Any = Body(...)):
    """
    接收 JSON 請求，支援直接傳入 list 或嵌套在 'csv_data' 或 'data' 欄位。
    """
    # 判斷資料來源
    if isinstance(raw, list):
        records = raw
    elif isinstance(raw, dict):
        if 'csv_data' in raw and isinstance(raw['csv_data'], list):
            records = raw['csv_data']
        elif 'data' in raw and isinstance(raw['data'], list):
            records = raw['data']
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON format: expected a list or a dict containing 'csv_data' or 'data'"
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON format: expected a list or object"
        )

    if not records:
        raise HTTPException(status_code=400, detail="Empty data list")

    # 建立 DataFrame
    df = pd.DataFrame(records)

        # 確保有 gwp 欄位供 fill_carbon_factors 檢查
    if 'gwp' not in df.columns:
        df['gwp'] = pd.NA
    # 填寫碳因子
    df = openai_helper.fill_carbon_factors(df)

    # 確保有 eta 欄位
    if 'eta' not in df.columns:
        df['eta'] = 0

    # 執行優化
    solutions = optimizer.optimize_materials(df)
    return {"solutions": solutions}

@app.post("/negotiation_note", response_model=None)
async def note(best_plan: Dict[str, Any]):
    note = openai_helper.generate_negotiation_note(best_plan)
    return {"note": note}
