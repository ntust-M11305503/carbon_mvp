import streamlit as st
import requests
import pandas as pd

BACKEND = "http://localhost:8000"

st.title("Carbon‑Aware Procurement MVP")

st.sidebar.header("1. 上傳報價 PDF")
uploaded = st.sidebar.file_uploader("Choose PDF", type=["pdf"])

if uploaded:
    # 將上傳的 PDF 發送給後端
    files = {"pdf": uploaded}
    resp = requests.post(f"{BACKEND}/upload_pdf", files=files)

    # 檢查是否成功解析 PDF
    if resp.ok:
        data = resp.json()  # 獲得解析後的資料
        
        # 直接將 CSV 資料處理為 DataFrame
        df = pd.DataFrame(data['csv_data'])  # 假設後端返回的是解析後的資料（列表格式）
        
        st.success(f"解析成功，共 {data['rows']} 筆")
        st.dataframe(df)  # 顯示解析結果的表格

        # 按鈕觸發進行優化的操作
        if st.button("進行優化 →"):
            opt = requests.post(f"{BACKEND}/optimize", json={"data": data['csv_data']})
            if opt.ok:
                sols = opt.json()["solutions"]
                df_res = pd.DataFrame(sols)
                st.dataframe(df_res)
                idx = st.selectbox("選擇方案", df_res["id"])

                # 生成議價稿
                if st.button("生成議價稿"):
                    note = requests.post(f"{BACKEND}/negotiation_note", json=sols[int(idx)])
                    if note.ok:
                        st.markdown(note.json()["note"])
    else:
        st.error(resp.text)
