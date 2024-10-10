
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

# 検索URLのリスト（複数の検索URLを指定）
SEARCH_URLS = [
    'https://suumo.jp/jj/chintai/ichiran/FR301FC001/?ar=030&bs=040&fw2=&pc=30&po1=25&po2=99&ra=014&rn=0185&ek=018503240&ek=018537650&ek=018534560&ek=018542410&ek=018540200&ek=018539710&ek=018528700&ek=018523100&ek=018509920&ek=018538720&ek=018538800&ek=018538760&ek=018538860&ek=018524790&ek=018512560&ek=018518510&ek=018530130&ek=018527340&ek=018503300&md=07&cb=10.0&ct=14.0&et=10&mb=50&mt=9999999&cn=20&ae=01851&co=1&tc=0400101&tc=0400501&tc=0400601&tc=0400301&tc=0400912&shkr1=03&shkr2=03&shkr3=03&shkr4=03',
    'https://suumo.jp/jj/chintai/ichiran/FR301FC001/?fw2=&ae=02301&ek=023017640&ek=023002000&ek=023016720&ek=023015340&ek=023016140&ek=023040800&ek=023034230&ek=023024700&ek=023037790&ek=023034220&ek=023022390&ek=023036850&ek=023007890&ek=023038250&ek=023038350&ek=023000820&ek=023000210&ek=023027240&ek=023024340&mt=9999999&cn=20&co=1&ra=014&et=15&tc=0400101&tc=0400501&tc=0400502&tc=0400601&tc=0400301&tc=0400302&tc=0400912&shkr1=03&ar=030&bs=040&ct=14.0&shkr3=03&shkr2=03&mb=50&md=07&rn=0230&shkr4=03&cb=10.0',
    'https://suumo.jp/jj/chintai/ichiran/FR301FC001/?ar=030&bs=040&fw2=&pc=30&po1=25&po2=99&ra=013&rn=0240&rn=0190&ek=024015920&ek=019035780&ek=019034330&ek=019040190&md=07&cb=10.0&ct=14.0&et=15&mb=50&mt=9999999&cn=20&rsnflg=1&co=1&tc=0400101&tc=0400501&tc=0400601&tc=0400301&tc=0400302&tc=0400902&tc=0400912&shkr1=03&shkr2=03&shkr3=03&shkr4=03'
]


# ファイル名の対応リスト
FILE_NAMES = [
    '南武線.json',
    '田園都市線.json',
    '町田周辺.json'
]

# データ取得関数
def fetch_suumo_data(search_url):
    listings = []
    page_num = 1  # 初期ページ番号
    while True:
        # ページ番号に応じた検索URLを構築
        paginated_url = f"{search_url}&pn={page_num}"
        response = requests.get(paginated_url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # SUUMOのリストページから必要なデータを抽出
        items = soup.select('.cassetteitem')
        if not items:  # アイテムがなければ終了
            break
        
        for item in items:
            title = item.select_one('.cassetteitem_content-title').text.strip() if item.select_one('.cassetteitem_content-title') else 'N/A'
            detail_link_element = item.select_one('.cassetteitem_other .js-cassette_link_href')
            url = 'https://suumo.jp' + detail_link_element['href'] if detail_link_element else None  # URLがない場合はNoneにする
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
        
        # 次のページへ
        page_num += 1
    
    return listings

# データをJSONに保存
def save_to_json(data, file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                old_data = json.load(file)
            old_df = pd.DataFrame(old_data)
        except json.JSONDecodeError:
            # ファイルが空または破損している場合は新規データフレームを作成
            old_df = pd.DataFrame()
    else:
        # ファイルが存在しない場合は新規データフレームを作成
        old_df = pd.DataFrame()
    
    new_df = pd.DataFrame(data)

    # 名前に含まれる「☆」「-」を削除
    if not old_df.empty and '名前' in old_df.columns:
        old_df['名前'] = old_df['名前'].str.replace('☆', '', regex=False).str.replace('-', '', regex=False)

    # 削除された物件を特定
    if not old_df.empty:
        merged_df = pd.merge(old_df, new_df, how='outer', on=['価格', '所在地', '間取り', '専有面積', '築年数', 'URL'], indicator=True)
        removed_properties = merged_df[merged_df['_merge'] == 'left_only']
        
        # 削除された物件があるかどうかを確認し、カラムの存在もチェック
        if not removed_properties.empty and all(col in removed_properties.columns for col in ['名前', '価格', '所在地', '間取り', '専有面積', '築年数', 'URL']):
            st.write("削除された物件情報:")
            st.dataframe(removed_properties[['名前', '価格', '所在地', '間取り', '専有面積', '築年数', 'URL']])
        else:
            st.write("削除された物件はありません。")
    
    # 新しいデータをファイルに保存
    final_df = pd.concat([old_df, new_df], ignore_index=True)
    final_df.drop_duplicates(subset=['価格', '所在地', '間取り', '専有面積', '築年数', 'URL'], keep='first', inplace=True)
    
    # JSONに保存
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(final_df.to_dict(orient='records'), file, ensure_ascii=False, indent=4)

# Streamlitアプリケーションの設定
st.title('スーパー☆SUUMO君')
st.write("このアプリではSUUMOから取得した物件情報を閲覧し、詳細リンクにアクセスできます。")

# 物件一覧を更新するボタン
if st.button("物件一覧を更新する"):
    with st.spinner('物件一覧を更新中です...'):
        for index, search_url in enumerate(SEARCH_URLS):
            json_file_path = FILE_NAMES[index]
            data = fetch_suumo_data(search_url)
            save_to_json(data, json_file_path)
        st.success("物件一覧が更新されました")

# ファイルの選択
files = [f for f in FILE_NAMES if os.path.exists(f)]
selected_file = st.selectbox('確認するJSONファイルを選択してください:', files)

# JSONファイルからデータを読み込む
if selected_file:
    df = pd.read_json(selected_file)
    
    if not df.empty:
        # データの表示
        st.write(f"ファイル名: {selected_file}")
        st.write("物件情報:")

        # 必要な情報を表示
        st.dataframe(df[['名前', '価格', '所在地', '間取り', '専有面積', '築年数', 'フラグ', 'URL']])

        # 各物件にアクセスするリンクとGoogle Mapsリンクを表示
        for index, row in df.iterrows():
            # フラグに基づいて物件名に「☆」を追加
            property_name = f"☆ {row['名前']}" if row['フラグ'] == '☆' else row['名前']

            st.markdown(f"### 物件名: {property_name}")
            st.markdown(f"**価格**: {row['価格']}  **所在地**: {row['所在地']}  **間取り**: {row['間取り']}  **専有面積**: {row['専有面積']}  **築年数**: {row['築年数']}")
            st.markdown(f"[詳細を見る]({row['URL']})")

            # Google Mapsで住所を開くリンクを追加
            google_maps_url = f"https://www.google.com/maps/search/?api=1&query={row['所在地']}"
            st.markdown(f"[Google Mapsで住所を表示する]({google_maps_url})")

            st.markdown("---")
    else:
        st.write("選択したファイルにはデータがありません。")

# 選択したデータを更新する処理
if st.button("選択したデータを更新"):
    json_file_path = selected_file
    for index, search_url in enumerate(SEARCH_URLS):
        if FILE_NAMES[index] == selected_file:
            with st.spinner('データを更新中です...'):
                data = fetch_suumo_data(search_url)
                save_to_json(data, json_file_path)
            st.success("選択したデータが更新されました")
