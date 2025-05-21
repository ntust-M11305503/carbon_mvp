from dotenv import load_dotenv
import os, json, pandas as pd
from openai import OpenAI

# 加載 .env 檔案
load_dotenv()

client = OpenAI()

# 從環境變數中取得 OpenAI API Key
OpenAI.api_key = os.getenv("OPENAI_API_KEY")

# 驗證是否成功讀取到 API Key
print("OpenAI API Key:", OpenAI.api_key)

def _chat(messages, model=None):
    model = model or os.getenv("MODEL", "gpt-4o-mini")
    resp = client.chat.completions.create(model=model, messages=messages)
    return resp.choices[0].message.content

def estimate_factor(row):
    item = row.get('item') or row.get('工程項目') or ''
    qty = row.get('qty') or row.get('數量') or ''
    unit = row.get('unit') or row.get('單位') or ''
    gwp = row.get('gwp', '未知')
    remark = row.get('remark', '') or row.get('說明', '')

    prompt = f"""
    材料/工程項目名稱: {item}
    數量: {qty}
    單位: {unit}
    已知 GWP: {gwp}
    說明: {remark}
    請根據你對建築工程標案與台灣常見造價經驗，「即使是大項、分類項，也要盡量推論或給一個常見平均值」，僅在資料毫無意義或純粹是格式分隔時（如純「合計」、「分隔線」），才填 null。
    所有回答皆需說明推論依據（如估算邏輯、比對經驗、合理假設等）。
    只回傳 JSON 格式，例如：
    {{
      "mean": 123.4,         // 合理值，若無法判斷請填 null
      "low": 100.0,          // 合理下限，若無法判斷請填 null
      "high": 150.0,         // 合理上限，若無法判斷請填 null
      "confidence": "推論依據與說明" // 必填
    }}
    """
    sys = "你是一位碳排估算助手，只回傳 JSON 格式 {mean, low, high, confidence}"
    txt = _chat([
        {"role": "system", "content": sys},
        {"role": "user", "content": prompt}
    ])
    try:
        data = json.loads(txt)
        return data  # 直接回傳所有欄位
    except Exception as e:
        print("JSON decode error:", e, "GPT回應：", txt)
        return {"mean": None, "low": None, "high": None, "confidence": "API/解析失敗"}

def fill_carbon_factors(df: pd.DataFrame):
    # 中英文自動映射
    col_map = {
        '項次':'idx', '工程項目':'item', '單位':'unit',
        '數量':'qty', '單價':'unit_price', '複價':'amount', '說明':'remark'
    }
    for zh, en in col_map.items():
        if en not in df.columns and zh in df.columns:
            df[en] = df[zh]
    if 'gwp' not in df.columns:
        df['gwp'] = None
    if 'qty' not in df.columns:
        df['qty'] = 1

    gwp_filled = []
    remarks = []
    for i, row in df.iterrows():
        value = row['gwp']
        if pd.isna(value) or value in (None, '', 0, '0'):
            est = estimate_factor(row)
            print(f"Row {i}: item={row.get('item') or row.get('工程項目')}, est_gwp={est}")
            gwp_filled.append(est.get("mean") if est.get("mean") is not None else 0)
            remarks.append(est.get("confidence") or "")
        else:
            gwp_filled.append(value)
            remarks.append(row.get('remark', '')[:50] if 'remark' in row else '')
    df['gwp'] = gwp_filled
    df['gwp_remark'] = remarks

    # 計算碳排量
    df['qty'] = pd.to_numeric(df['qty'], errors='coerce').fillna(1)
    df['碳排放量'] = df['gwp'] * df['qty']
    return df

def generate_negotiation_note(best_plan: dict):
    sys = "你是採購談判顧問，請用專業但友善的語氣。"
    user = f"""以下是我們選定的採購方案:
{json.dumps(best_plan, ensure_ascii=False, indent=2)}
請幫我撰寫對供應商的一段議價話術，並建議可替代的低碳材料。
"""
    return _chat([{"role": "system", "content": sys},
                  {"role": "user", "content": user}])
