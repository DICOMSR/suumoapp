
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import json
from datetime import datetime
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import streamlit as st


# GitHubのリポジトリとファイル設定
GITHUB_REPO = "DICOMSR/suumoapp"
GITHUB_FILE_PATHS = ["南武線.json", "田園都市線.json", "町田周辺.json"]
GITHUB_API_URL_TEMPLATE = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{{}}"
GITHUB_RAW_URL_TEMPLATE = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{{}}"

# GitHubトークン（GitHub APIを使うために必要）
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
# GitHubからJSONを取得する関数
def fetch_json_from_github(file_path):
    try:
        raw_url = GITHUB_RAW_URL_TEMPLATE.format(file_path)
        response = requests.get(raw_url)
        response.raise_for_status()  # エラーチェック
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"GitHubからJSONを取得できません: {e}")
        return None

# GitHubにJSONを保存する関数
def save_json_to_github(file_path, data):
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    api_url = GITHUB_API_URL_TEMPLATE.format(file_path)

    # 現在のファイルのSHAを取得する
    get_response = requests.get(api_url, headers=headers)
    if get_response.status_code == 200:
        sha = get_response.json().get("sha")
    else:
        sha = None  # 新規作成の場合はSHAが不要

    # GitHub APIにデータを書き込む
    payload = {
        "message": "Update JSON file via Streamlit",
        "content": json.dumps(data).encode('utf-8').decode('ascii'),  # データをエンコードして送信
        "branch": "main"
    }
    if sha:
        payload["sha"] = sha  # 既存ファイルの更新に必要

    response = requests.put(api_url, headers=headers, json=payload)
    if response.status_code == 201 or response.status_code == 200:
        st.success(f"ファイル {file_path} がGitHubに保存されました。")
    else:
        st.error(f"GitHubに保存できませんでした: {response.json()}")

# 検索URLのリスト（複数の検索URLを指定）
SEARCH_URLS = [
    'https://suumo.jp/jj/chintai/ichiran/FR301FC001/?ar=030&bs=040&fw2=&pc=30&po1=25&po2=99&ra=014&rn=0185&ek=018503240&ek=018537650&ek=018534560&ek=018542410&ek=018540200&ek=018539710&ek=018528700&ek=018523100&ek=018509920&ek=018538720&ek=018538800&ek=018538760&ek=018538860&ek=018524790&ek=018512560&ek=018518510&ek=018530130&ek=018527340&ek=018503300&md=07&cb=10.0&ct=14.0&et=10&mb=50&mt=9999999&cn=20&ae=01851&co=1&tc=0400101&tc=0400501&tc=0400601&tc=0400301&tc=0400912&shkr1=03&shkr2=03&shkr3=03&shkr4=03',
    'https://suumo.jp/jj/chintai/ichiran/FR301FC001/?fw2=&ae=02301&ek=023017640&ek=023002000&ek=023016720&ek=023015340&ek=023016140&ek=023040800&ek=023034230&ek=023024700&ek=023037790&ek=023034220&ek=023022390&ek=023036850&ek=023007890&ek=023038250&ek=023038350&ek=023000820&ek=023000210&ek=023027240&ek=023024340&mt=9999999&cn=20&co=1&ra=014&et=15&tc=0400101&tc=0400501&tc=0400502&tc=0400601&tc=0400301&tc=0400302&tc=0400912&shkr1=03&ar=030&bs=040&ct=14.0&shkr3=03&shkr2=03&mb=50&md=07&rn=0230&shkr4=03&cb=10.0',
    'https://suumo.jp/jj/chintai/ichiran/FR301FC001/?ar=030&bs=040&fw2=&pc=30&po1=25&po2=99&ra=013&rn=0240&rn=0190&ek=024015920&ek=019035780&ek=019034330&ek=019040190&md=07&cb=10.0&ct=14.0&et=15&mb=50&mt=9999999&cn=20&rsnflg=1&co=1&tc=0400101&tc=0400501&tc=0400601&tc=0400301&tc=0400302&tc=0400902&tc=0400912&shkr1=03&shkr2=03&shkr3=03&shkr4=03'
]

# データ取得関数
def fetch_suumo_data(search_url):
    listings = []
    page_num = 1  # 初期ページ番号
    while True:
        paginated_url = f"{search_url}&pn={page_num}"
        response = requests.get(paginated_url)
        soup = BeautifulSoup(response.text, 'html.parser')

        items = soup.select('.cassetteitem')
        if not items:  # アイテムがなければ終了
            break
        
        for item in items:
            title = item.select_one('.cassetteitem_content-title').text.strip() if item.select_one('.cassetteitem_content-title') else 'N/A'
            detail_link_element = item.select_one('.cassetteitem_other .js-cassette_link_href')
            url = 'https://suumo.jp' + detail_link_element['href'] if detail_link_element else None
            price = item.select_one('.cassetteitem_price--rent').text.strip() if item.select_one('.cassetteitem_price--rent') else 'N/A'
            address = item.select_one('.cassetteitem_detail-col1').text.strip() if item.select_one('.cassetteitem_detail-col1') else 'N/A'
            floor_plan = item.select_one('.cassetteitem_madori').text.strip() if item.select_one('.cassetteitem_madori') else 'N/A'
            area = item.select_one('.cassetteitem_menseki').text.strip() if item.select_one('.cassetteitem_menseki') else 'N/A'
            age = item.select_one('.cassetteitem_detail-col3').get_text(separator=' ', strip=True) if item.select_one('.cassetteitem_detail-col3') else 'N/A'
            date = datetime.now().isoformat()

            listings.append({
                '名前': title,
                '価格': price,
                '所在地': address,
                '間取り': floor_plan,
                '専有面積': area,
                '築年数': age,
                '取得日': date,
                'URL': url,
                'フラグ': '-'  # 初期フラグは既存として「-」を設定
            })
        
        page_num += 1  # 次のページへ
    
    return listings

# データをJSONに保存
def save_to_json(data, json_file_path):
    existing_data = fetch_json_from_github(json_file_path)
    if existing_data:
        old_df = pd.DataFrame(existing_data)
    else:
        old_df = pd.DataFrame()

    new_df = pd.DataFrame(data)

    if not old_df.empty:
        old_df['名前'] = old_df['名前'].str.replace('☆', '', regex=False).str.replace('-', '', regex=False)

    new_df['フラグ'] = '-'
    if not old_df.empty:
        merged_df = pd.merge(new_df, old_df, how='left', on=['価格', '所在地', '間取り', '専有面積', '築年数'], indicator=True)
        new_properties = merged_df[merged_df['_merge'] == 'left_only']
        new_df.loc[new_df['URL'].isin(new_properties['URL']), 'フラグ'] = '☆'

    # 削除された物件を表示
    if not old_df.empty:
        merged_df = pd.merge(old_df, new_df, how='outer', on=['価格', '所在地', '間取り', '専有面積', '築年数', 'URL'], indicator=True)
        removed_properties = merged_df[merged_df['_merge'] == 'left_only']
        if not removed_properties.empty:
            st.write("削除された物件:")
            st.dataframe(removed_properties[['名前', '価格', '所在地', '間取り', '専有面積', '築年数', 'URL']])

    final_df = pd.concat([old_df, new_df], ignore_index=True)
    final_df.drop_duplicates(subset=['価格', '所在地', '間取り', '専有面積', '築年数', 'URL'], keep='first', inplace=True)

    save_json_to_github(json_file_path, final_df.to_dict(orient='records'))

# Streamlitアプリの設定
st.title('スーパー☆SUUMO君')

if st.button("物件一覧を更新する"):
    with st.spinner('物件一覧を更新中です...'):
        for index, search_url in enumerate(SEARCH_URLS):
            json_file_path = GITHUB_FILE_PATHS[index]
            data = fetch_suumo_data(search_url)
            save_to_json(data, json_file_path)
        st.success("物件一覧が更新されました")

# ファイルの選択
selected_file = st.selectbox('確認するJSONファイルを選択してください:', GITHUB_FILE_PATHS)

# JSONファイルからデータを読み込む
if selected_file:
    json_data = fetch_json_from_github(selected_file)
    if json_data:
        df = pd.DataFrame(json_data)
        if not df.empty:
            st.write(f"ファイル名: {selected_file}")
            st.write("物件情報:")
            st.dataframe(df[['名前', '価格', '所在地', '間取り', '専有面積', '築年数', 'フラグ', 'URL']])

            for _, row in df.iterrows():
                property_name = f"☆ {row['名前']}" if row['フラグ'] == '☆' else row['名前']
                st.markdown(f"### 物件名: {property_name}")
                st.markdown(f"**価格**: {row['価格']}  **所在地**: {row['所在地']}  **間取り**: {row['間取り']}  **専有面積**: {row['専有面積']}  **築年数**: {row['築年数']}")
                st.markdown(f"[詳細を見る]({row['URL']})")
                google_maps_url = f"https://www.google.com/maps/search/?api=1&query={row['所在地']}"
                st.markdown(f"[Google Mapsで住所を表示する]({google_maps_url})")
                st.markdown("---")
