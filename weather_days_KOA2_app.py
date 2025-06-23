import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import AMD_Tools4 as amd
import json
import os

# --- ファイル名（ローカル保存用） ---
LOC_FILE = "locations.json"

# --- 初期地点（JSONがない場合のデフォルト） ---
DEFAULT_LOCATIONS = {
    "KOA山1（洗馬、標高1035m）": [36.10615778, 137.8787694],
    "KOA山2（洗馬、標高1017m）": [36.10599167, 137.8787083],
    "KOA山3（洗馬、標高1007m）": [36.10616111, 137.8790889],
    "KOA山4（洗馬、標高1005m）": [36.10617778, 137.8789667],
    "KOA5WW（West Wing、標高783ｍ）": [35.89755278, 137.9560553],
    "KOA6（手良、標高806ｍ）": [35.87172194, 138.0164028],
    "KOA7（手良、標高791ｍ）": [35.87127222, 138.0160833]
}

# --- JSON読み込み関数 ---
def load_locations():
    if os.path.exists(LOC_FILE):
        with open(LOC_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return DEFAULT_LOCATIONS

# --- JSON保存関数 ---
def save_locations(locations):
    with open(LOC_FILE, 'w', encoding='utf-8') as f:
        json.dump(locations, f, ensure_ascii=False, indent=2)

# --- セッション状態に読み込み ---
if "location_history" not in st.session_state:
    st.session_state.location_history = load_locations()

# --- 気象要素の一覧 ---
ELEMENT_OPTIONS = {
    "日平均気温 (TMP_mea)": "TMP_mea",
    "日最高気温 (TMP_max)": "TMP_max",
    "日最低気温 (TMP_min)": "TMP_min",
    "降水量 (APCP)": "APCP",
    "降水量高精度 (APCPRA)": "APCPRA",
    "降水の有無 (OPR)": "OPR",
    "日照時間 (SSD)": "SSD",
    "全天日射量 (GSR)": "GSR",
    "下向き長波放射量 (DLR)": "DLR",
    "相対湿度 (RH)": "RH",
    "風速 (WIND)": "WIND",
    "積雪深 (SD)": "SD",
    "積雪水量 (SWE)": "SWE",
    "降雪水量 (SFW)": "SFW",
    "予報気温の確からしさ (PTMP)": "PTMP"
}

# --- タイトルと説明 ---
st.title("メッシュ気象データ取得アプリ")
st.write("地点を選んで山の気象データを取得します。Created by O. Watanabe, Shinshu Univ.")

# --- 地点の追加フォーム ---
st.subheader("1. 観測地点の選択または追加")

with st.expander("📝 新しい観測地点を追加"):
    new_name = st.text_input("地点名")
    new_lat = st.number_input("緯度", format="%.6f")
    new_lon = st.number_input("経度", format="%.6f")
    if st.button("地点を追加"):
        if new_name and (new_lat and new_lon):
            st.session_state.location_history[new_name] = [new_lat, new_lon]
            save_locations(st.session_state.location_history)
            st.success(f"地点「{new_name}」を追加しました。")
        else:
            st.warning("地点名、緯度、経度をすべて入力してください。")

# --- 地点選択 ---
selected_location = st.selectbox("観測地点を選んでください", list(st.session_state.location_history.keys()))
lat, lon = st.session_state.location_history[selected_location]
st.success(f"選択された地点：{selected_location}（緯度 {lat:.4f}, 経度 {lon:.4f}）")

# --- 取得期間・要素選択 ---
st.subheader("2. 取得期間と気象要素の指定（26日先まで）")
start_date = st.date_input("開始日")
end_date = st.date_input("終了日")
selected_labels = st.multiselect(
    "取得する気象要素（記号付き）※複数選択可",
    list(ELEMENT_OPTIONS.keys()),
    default=["日平均気温 (TMP_mea)"]
)

# --- データ取得ボタン ---
if st.button("データを取得"):
    if start_date >= end_date:
        st.error("終了日は開始日より後の日付にしてください。")
    elif not selected_labels:
        st.error("1つ以上の気象要素を選択してください。")
    else:
        try:
            itsu = [str(start_date), str(end_date)]
            doko = [lat, lat, lon, lon]
            records = {}
            normals = {}
            tim_ref = None

            for label in selected_labels:
                code = ELEMENT_OPTIONS[label]
                data, tim, _, _ = amd.GetMetData(code, itsu, doko, cli=False)
                records[label + "（AMD）"] = data[:, 0, 0]
                norm_data, norm_tim, _, _ = amd.GetMetData(code, itsu, doko, cli=True)
                normals[label + "（平年値）"] = norm_data[:, 0, 0]
                if tim_ref is None:
                    tim_ref = pd.to_datetime(tim)

            df = pd.DataFrame({**records, **normals})
            df.insert(0, "日付", tim_ref)

            # 表示
            st.subheader("3. データ表示（AMDと平年値）")
            st.dataframe(df)

            st.subheader("4. 折れ線グラフ（AMD vs 平年値）")
            for label in selected_labels:
                actual = label + "（AMD）"
                normal = label + "（平年値）"
                st.write(f"### {label} の推移（AMDと平年値）")
                fig, ax = plt.subplots()
                ax.plot(df["日付"], df[actual], marker='o', label='AMD')
                ax.plot(df["日付"], df[normal], marker='x', linestyle='--', label='平年値')
                ax.set_xlabel("日付")
                ax.set_ylabel(label)
                ax.tick_params(axis='x', labelrotation=45)
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                ax.legend()
                st.pyplot(fig)

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")