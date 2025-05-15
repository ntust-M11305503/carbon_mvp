from dotenv import load_dotenv
import os, json, pandas as pd
from openai import OpenAI
client = OpenAI()

# 加載 .env 檔案
load_dotenv()

# 從環境變數中取得 OpenAI API Key
OpenAI.api_key = os.getenv("OPENAI_API_KEY")

# 驗證是否成功讀取到 API Key
print("OpenAI API Key:", OpenAI.api_key)

def _chat(messages, model=None):
    model = model or os.getenv("MODEL", "gpt-4o-mini")
    resp = client.chat.completions.create(model=model, messages=messages)
    return resp.choices[0].message.content

def estimate_factor(row):
    prompt = f"""材料: {row['item']}
數量: {row['qty']}
已知 GWP: {row.get('gwp', '未知')}
如果未知，請根據工程常用值(kg CO2e/t)估算給出 mean,low,high。"
"""
    sys = "你是一位碳排估算助手，回傳 JSON 格式 {mean, low, high, confidence}"
    txt = _chat([{"role": "system", "content": sys},
                 {"role": "user", "content": prompt}])
    try:
        data = json.loads(txt)
        return data.get("mean")
    except Exception:
        return None

def fill_carbon_factors(df: pd.DataFrame):
    gwp_filled = []
    for _, row in df.iterrows():
        if pd.isna(row['gwp']) or row['gwp']==0:
            est = estimate_factor(row)
            gwp_filled.append(est or 1000)
        else:
            gwp_filled.append(row['gwp'])
    df['gwp'] = gwp_filled
    return df

def generate_negotiation_note(best_plan: dict):
    sys = "你是採購談判顧問，請用專業但友善的語氣。"
    user = f"""以下是我們選定的採購方案:
{json.dumps(best_plan, ensure_ascii=False, indent=2)}
請幫我撰寫對供應商的一段議價話術，並建議可替代的低碳材料。
"""
    return _chat([{"role": "system", "content": sys},
                  {"role": "user", "content": user}])
