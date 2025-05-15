import streamlit as st
import requests
import pandas as pd

BACKEND = "http://localhost:8000"

st.title("Carbon-Aware Procurement MVP")
st.sidebar.header("1. 上傳報價 PDF")

uploaded = st.sidebar.file_uploader("Choose PDF", type=["pdf"])
if not uploaded:
    st.sidebar.info("請先上傳 PDF 檔以解析表格。")
    st.stop()

# 上傳並取得原始資料
files = {"pdf": uploaded}
resp = requests.post(f"{BACKEND}/upload_pdf", files=files)
if not resp.ok:
    st.sidebar.error(resp.text)
    st.stop()

# 建立 DataFrame
data = resp.json()
raw_df = pd.DataFrame(data["csv_data"])
st.sidebar.success(f"解析成功，共 {len(raw_df)} 列")

# 顯示原始表格
if st.sidebar.checkbox("顯示原始表格"):
    st.subheader("原始表格")
    st.dataframe(raw_df)

# 整理邏輯：根據次級標籤行 mapping extras 欄位，對齊至主欄位
desired_cols = ['項次','工程項目','單位','數量','單價','複價','說明']
extras_cols = [c for c in raw_df.columns if c not in desired_cols]

# 建立 mapping: extras 欄位 -> desired 欄位
mapping = {}
aligned_rows = []
for _, raw_row in raw_df.iterrows():
    # 判斷是否為次級標籤行：所有 desired_cols 為空、至少一個 extras 為 desired 標籤
    is_label = True
    any_extra = False
    for c in extras_cols:
        val = raw_row.get(c)
        if val not in (None, ''):
            any_extra = True
            if val not in desired_cols:
                is_label = False
    for c in desired_cols:
        if raw_row.get(c) not in (None, ''):
            is_label = False
    if is_label and any_extra:
        # 更新 mapping
        for c in extras_cols:
            val = raw_row.get(c)
            if val in desired_cols:
                mapping[c] = val
        # 對於次級標籤行，也保留一筆資料，用以呈現原始位置
        new_row = {c: '' for c in desired_cols}
        # 將 extras 中的標籤顯示在對應欄位
        for c in extras_cols:
            val = raw_row.get(c)
            if val in desired_cols:
                new_row[val] = val
        aligned_rows.append(new_row)
        continue
    # 一般資料列：先以原本主欄位填值
    new_row = {c: raw_row.get(c, '') for c in desired_cols}
    # 再以 mapping 對應 extras 欄位資料
    for c in extras_cols:
        val = raw_row.get(c)
        if val not in (None, '') and mapping.get(c):
            if new_row.get(mapping[c], '') in (None, ''):
                new_row[mapping[c]] = val
    aligned_rows.append(new_row)

# 取得對齊後 DataFrame
disp_df = pd.DataFrame(aligned_rows)

# 找出各段標題行：項次~說明全空，工程項目非空
mask_title = (
    (disp_df['項次']=='') & (disp_df['單位']=='') & (disp_df['數量']=='') &
    (disp_df['單價']=='') & (disp_df['複價']=='') & (disp_df['說明']=='') &
    (disp_df['工程項目']!='')
)
title_idxs = disp_df[mask_title].index.tolist()

# 合併成單一表格：插入粗體標題行與資料
rows = []
if title_idxs:
    title_idxs.append(len(disp_df))
    for i in range(len(title_idxs)-1):
        idx = title_idxs[i]
        title = disp_df.at[idx,'工程項目']
        # 標題行
        rows.append({c: '' for c in desired_cols})
        rows[-1]['工程項目'] = f"**{title}**"
        # 資料列
        block = disp_df.iloc[idx+1:title_idxs[i+1]].reset_index(drop=True)
        for _, r in block.iterrows():
            rows.append(r.to_dict())
    df_merged = pd.DataFrame(rows)
else:
    df_merged = None

# 按鈕：整理表格
if st.sidebar.button("整理表格"):
    if df_merged is not None:
        st.subheader("整理後表格：帶標題分段與對齊")
        # HTML 方式呈現粗體
        st.write(df_merged.to_html(index=False, escape=False), unsafe_allow_html=True)
    else:
        st.error("整理失敗：無法偵測到任何段落標題。")

# 按鈕：進行優化
if st.sidebar.button("進行優化"):
    opt = requests.post(f"{BACKEND}/optimize", json={"data": data.get('csv_data')})
    if not opt.ok:
        st.error(opt.text)
        st.stop()
    sols = opt.json().get("solutions", [])
    st.subheader("優化結果")
    st.table(pd.DataFrame(sols))
    plan_id = st.selectbox("選擇方案", [s['id'] for s in sols])
    if st.button("生成議價稿"):
        note = requests.post(f"{BACKEND}/negotiation_note", json=next(s for s in sols if s['id']==plan_id))
        if note.ok:
            st.subheader("議價稿")
            st.markdown(note.json().get("note", ""))
        else:
            st.error(note.text)
