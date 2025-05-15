import pdfplumber
import pandas as pd
from pathlib import Path

def pdf_to_dataframe(pdf_path: Path) -> pd.DataFrame:
    """
    使用 pdfplumber 擷取 PDF 中的表格，並轉為 DataFrame。
    """
    # 確保傳入的是字串路徑
    pdf_file = str(pdf_path)
    # 開啟 PDF
    with pdfplumber.open(pdf_file) as pdf:
        all_tables = []
        for page in pdf.pages:
            # extract_tables 回傳 list[list[list]]
            tables = page.extract_tables()
            for table in tables:
                all_tables.append(table)
    if not all_tables:
        raise ValueError("PDF 中未偵測到任何表格。")

    # 只取第一個表格作為預設
    header, *rows = all_tables[0]
    df = pd.DataFrame(rows, columns=header)

    # 去除字串前後空白
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    return df

# =====================================================================
# 如果未來需要 OCR+Regex 的備援，也可保留以下函式：
# def parse_flat_estimate(raw_text: str) -> pd.DataFrame:
#     ...
