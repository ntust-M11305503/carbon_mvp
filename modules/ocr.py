import pdfplumber
import pandas as pd
from pathlib import Path


def pdf_to_dataframe(pdf_path: Path) -> pd.DataFrame:
    """
    使用 pdfplumber 擷取 PDF 中所有表格，將每個表格的標頭與資料行解析後串接，
    並回傳合併後的 DataFrame。
    """
    pdf_file = str(pdf_path)
    dfs = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                # 每個 table 至少要有 header + 一列資料
                if not table or len(table) < 2:
                    continue
                header, *rows = table
                # 清理 header 前後空白並處理 None
                cleaned = [h.strip() if isinstance(h, str) else '' for h in header]
                # 生成唯一欄名，避免重複導致 reindex 錯誤
                seen = {}
                unique_header = []
                for h in cleaned:
                    if h in seen:
                        seen[h] += 1
                        unique_header.append(f"{h}.{seen[h]}")
                    else:
                        seen[h] = 0
                        unique_header.append(h)
                # 建立 DataFrame
                df = pd.DataFrame(rows, columns=unique_header)
                # 清理 cell 前後空白
                df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
                dfs.append(df)
    if not dfs:
        raise ValueError("PDF 中未偵測到任何表格。")
    combined = pd.concat(dfs, ignore_index=True)
    # 清理全空列
    combined = combined.dropna(how='all').reset_index(drop=True)
    # 將 NaN 替換成 None，以便 JSON 序列化
    combined = combined.where(pd.notnull(combined), None)
    return combined

# =====================================================================
# 備援方案：對扁平化 CSV 文本使用 parse_flat_estimate 進行手動解析
# def parse_flat_estimate(raw_text: str) -> pd.DataFrame:
#     ...
