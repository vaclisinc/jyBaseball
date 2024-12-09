import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
import requests
import time
import hashlib

apiEndpoint = "https://script.google.com/macros/s/AKfycbyEqnJGcnvQN8IDg6mXrvWT78l5U8VpxR7Sp6xuzv299M9UyO5qq5VfmH_2BbfR1IehcQ/exec"

sheet = 'https://docs.google.com/spreadsheets/d/1n3Xt5iemJ3WWjlksEaU6JfNDv_9FX4CStTzjayMRwEU/edit#gid=0'
url_data = sheet.replace('/edit#gid=', '/export?format=csv&gid=')

last_hash = None

def calculate_avg(df):
    avg_dict = {}
    unique_positions = sorted(df['position'].unique())
    unique_names = df['name'].unique()

    for position in unique_positions:
        avg_dict[position] = {}
        for name in unique_names:
            single_count = (df[(df['name'] == name) & (
                df['position'] == position)]['result'] == '一安 Single').sum()
            double_count = (df[(df['name'] == name) & (
                df['position'] == position)]['result'] == '二安 Double').sum()
            triple_count = (df[(df['name'] == name) & (
                df['position'] == position)]['result'] == '三安 Triple').sum()
            hr_count = (df[(df['name'] == name) & (
                df['position'] == position)]['result'] == '全壘打 Home Run').sum()
            total_hits = single_count + double_count + triple_count + hr_count
            total_at_bats = (df[(df['name'] == name) & (df['position'] == position)]['result'].isin(['一安 Single', '二安 Double', '三安 Triple', '全壘打 Home Run',
                             '外飛 Field Out', '失誤 Field Error', '三振 Strikeout']) & ~df[(df['name'] == name) & (df['position'] == position)]['result'].isna()).sum()

            if total_at_bats > 0:
                avg = total_hits / total_at_bats
                avg_dict[position][name] = avg
            else:
                avg_dict[position][name] = None

    avg_df = pd.DataFrame(avg_dict)
    avg_df.index.name = 'name'
    return avg_df


def refreshData():
    print("\rStart refresh", end="")
    df = pd.read_csv(url_data)
    avg_df = calculate_avg(df)
    avg_df = avg_df.transpose()

    # Get exist image
    existImageDataRequest = requests.get(apiEndpoint + '?n=image&width=2')
    existImageData = existImageDataRequest.json()
    # keys = existImageData[:1][0]
    values = existImageData[1:]
    existImageData = {i[0]: i[1] for i in values}

    unique_names = df['name'].unique()
    new_frames = {}  # everybody's 9 block
    for name in unique_names:
        new_frame = pd.DataFrame(0, index=range(
            0, 8), columns=range(0, 8), dtype=float)
        for i in range(0, 3):
            for j in range(0, 3):
                value = avg_df.loc[3*i+j+1, name]
                new_frame.loc[i*2+1, j*2+1] = value
                new_frame.loc[i*2+1, j*2+2] = value
                new_frame.loc[i*2+2, j*2+1] = value
                new_frame.loc[i*2+2, j*2+2] = value
        value = avg_df.loc[10, name]
        for y, x in ((0, 0), (1, 0), (2, 0), (3, 0), (0, 1), (0, 2), (0, 3)):
            new_frame.loc[y, x] = value
        value = avg_df.loc[11, name]
        for y, x in ((0, 4), (0, 5), (0, 6), (0, 7), (1, 7), (2, 7), (3, 7)):
            new_frame.loc[y, x] = value
        value = avg_df.loc[12, name]
        for y, x in ((4, 0), (5, 0), (6, 0), (7, 0), (7, 1), (7, 2), (7, 3)):
            new_frame.loc[y, x] = value
        value = avg_df.loc[13, name]
        for y, x in ((7, 4), (7, 5), (7, 6), (7, 7), (6, 7), (5, 7), (4, 7)):
            new_frame.loc[y, x] = value
        new_frames[name] = new_frame
        # print(new_frame)

    for playerName in new_frames:
        plt.clf()
        playerFrame = new_frames[playerName]
        # sns_plot = sns.heatmap(playerFrame, center=0.5,
        #                        cmap='Blues', square=True, annot=True, fmt=".3f")
        sns_plot = sns.heatmap(playerFrame, center=0.3,vmin=0, vmax=1,
                               cmap='Blues', square=True, fmt=".3f")
        plt.xticks([])
        plt.yticks([])
        for i in range(0, 3):
            for j in range(0, 3):
                value = playerFrame.iloc[i*2+1, j*2+1]
                color = 'black'
                if pd.isna(value):
                    value = 'NO DATA'
                    color = 'red'
                else:
                    value = "%.3f" % value
                sns_plot.text(j*2+2, i*2+2, value,
                              ha='center', va='center', color=color)
        for i, j in ((0, 0), (0, 4), (7, 0),(7, 4)):
                value = playerFrame.iloc[i, j]
                color = 'black'
                if pd.isna(value):
                    value = 'NO DATA'
                    color = 'red'
                else:
                    value = "%.3f" % value
                sns_plot.text(j+2, i+0.5, value,
                              ha='center', va='center', color=color)

        # for i in range(playerFrame.shape[0]):
        #     for j in range(playerFrame.shape[1]):
        #         if pd.isna(playerFrame.iloc[i, j]):
        #             sns_plot.text(j + 0.5, i + 0.5, 'NO DATA',
        #                           ha='center', va='center', color='red')
        
        # Create image
        newImageByts = io.BytesIO()
        plt.savefig(newImageByts, format='png', bbox_inches='tight')
        newImageByts.seek(0)
        newImageBase64 = base64.b64encode(newImageByts.read()).decode()

        # Send image
        result = None
        if playerName not in existImageData or existImageData[playerName] != newImageBase64:
            result = requests.post(apiEndpoint + '?n=image', json={
                "key": playerName,
                "values": [newImageBase64]
            })
            print()
            print(playerFrame)
            if result.status_code == 200:
                print("Success")
            else:
                print("Error")

        if playerName in existImageData:
            existImageData.pop(playerName)

    # Delete nonexist player
    requests.post(apiEndpoint + '?n=image&t=d', json={
        "key": [i for i in existImageData],
    })

    plt.close()
    print('\rDone          ', end="")

while True:
    try:
        # 計算 CSV 資料的哈希值
        response = requests.get(url_data)
        if response.status_code == 200:
            new_hash = hashlib.md5(response.content).hexdigest()

            # 檢查資料是否有變動
            if new_hash != last_hash:
                print("Data changed. Refreshing...")
                refreshData()
                last_hash = new_hash
            else:
                print("No changes detected")
        else:
            print(f"Failed to fetch data: HTTP {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

    time.sleep(10)  # 增加間隔時間