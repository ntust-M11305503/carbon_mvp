import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from modules import ocr, optimizer, openai_helper
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

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
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    return {
        "csv_path": str(csv_path),
        "rows": len(df),
        "csv_data": df.to_dict(orient="records")
    }

@app.post("/format_table")
async def format_table(raw: dict = Body(...)):
    # 取得 records
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

    # 統一欄位名，並保留所有需要的欄位
    main_cols = ['項次', '工程項目', '單位', '數量', '單價', '複價', '說明']
    # 重新整理 mapping + 萃取欄位
    df = pd.DataFrame(records)
    df = df.reindex(columns=main_cols).fillna('')
    # 過濾掉非明細的行
    not_header = ~df['項次'].astype(str).str.contains('項次', na=False)
    not_title = ~(
        (df['項次'] == '') & (df['單位'] == '') & (df['數量'] == '') & (df['單價'] == '') &
        (df['複價'] == '') & (df['說明'] == '') & (df['工程項目'] != '')
    )
    not_summary = ~(
        df['工程項目'].astype(str).str.contains('小計|合計|subtotal|total', na=False) |
        df['項次'].astype(str).str.contains('小計|合計|subtotal|total', na=False)
    )
    # 去除全空行
    is_not_empty = ~(df == '').all(axis=1)
    mask = not_header & not_title & not_summary & is_not_empty
    df_clean = df[mask].reset_index(drop=True)

    # 輸出資料結構（留著統一格式）
    return {"csv_data": df_clean.to_dict(orient="records")}

@app.post("/fill_carbon_factors")
async def fill_carbon_factors(raw: Any = Body(...)):
    if isinstance(raw, dict) and 'data' in raw and isinstance(raw['data'], list):
        records = raw['data']
    else:
        raise HTTPException(status_code=400, detail="Invalid input")
    df = pd.DataFrame(records)
    from modules import openai_helper
    df = openai_helper.fill_carbon_factors(df)

    # **確保 gwp/qty 為數值型態**
    for col in ['gwp', 'qty']:
        if col not in df.columns:
            df[col] = 0
    df['gwp'] = pd.to_numeric(df['gwp'], errors='coerce').fillna(0)
    df['qty'] = pd.to_numeric(df['qty'], errors='coerce').fillna(0)

    df['碳排放量'] = df['gwp'] * df['qty']
    return {"csv_data": df.to_dict(orient="records")}

@app.post("/save_csv")
async def save_csv(raw: Any = Body(...)):
    filename = os.path.splitext(os.path.basename(raw.get("filename", "")))[0]
    data = raw.get("data")
    if not filename or not isinstance(data, list):
        raise HTTPException(status_code=400, detail="Invalid input or missing filename")
    df = pd.DataFrame(data)
    sorted_csv_name = f"{filename}_sorted.csv"
    csv_path = DATA_DIR / sorted_csv_name
    df = df.loc[:, ~df.columns.duplicated()]
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    return {"csv_path": str(csv_path), "rows": len(df)}

@app.post("/optimize", response_model=None)
async def optimize(raw: Any = Body(...)):
    # 一律先走欄位標準化
    # 可以直接呼叫 format_table 的同名欄位 mapping
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

    # 新增這段！直接複製你 /format_table 的欄位 rename
    df = pd.DataFrame(records)
    df = df.rename(columns={
        '項次':'idx','工程項目':'item','Item':'item',
        '單位':'unit','Unit':'unit',
        '數量':'qty','Quant':'qty',
        '單價':'unit_price','Unit Price':'unit_price',
        '複價':'amount','Amount':'amount'
    })
    for col in ['item','unit','qty','unit_price','amount']:
        if col not in df.columns:
            df[col] = None

    # 清理數字欄位
    df['qty'] = pd.to_numeric(df['qty'], errors='coerce').fillna(0).astype(int)
    df['unit_price'] = pd.to_numeric(df['unit_price'], errors='coerce').fillna(0).astype(int)
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0).astype(int)

    if '說明' in df.columns:
        df['remark'] = df['說明']

    # 下面照原本繼續
    if 'gwp' not in df.columns:
        df['gwp'] = pd.NA
    df = openai_helper.fill_carbon_factors(df)

    if 'eta' not in df.columns:
        df['eta'] = 0

    solutions = optimizer.optimize_materials(df)
    return {"solutions": solutions}
