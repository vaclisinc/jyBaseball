from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import numpy as np
import io
import base64
import requests
import matplotlib.pyplot as plt
import seaborn as sns
import time
from fastapi.middleware.cors import CORSMiddleware


# FastAPI 應用
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 你可以根據需求設置具體允許的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 設定 Google Sheets API 的範圍
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# 加載服務帳戶憑證
creds = Credentials.from_service_account_file("/root/jybaseball/v2/credentials.json", scopes=SCOPES)
client = gspread.authorize(creds)

# 打開你的 Google Sheets
spreadsheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1n3Xt5iemJ3WWjlksEaU6JfNDv_9FX4CStTzjayMRwEU/edit#gid=0")

# 定義資料處理函數
def calculate_avg(df):
    avg_dict = {}
    unique_positions = sorted(df['position'].unique())
    unique_names = df['name'].unique()

    for position in unique_positions:
        avg_dict[position] = {}
        for name in unique_names:
            single_count = (df[(df['name'] == name) & (df['position'] == position)]['result'] == '一安 Single').sum()
            double_count = (df[(df['name'] == name) & (df['position'] == position)]['result'] == '二安 Double').sum()
            triple_count = (df[(df['name'] == name) & (df['position'] == position)]['result'] == '三安 Triple').sum()
            hr_count = (df[(df['name'] == name) & (df['position'] == position)]['result'] == '全壘打 Home Run').sum()
            total_hits = single_count + double_count + triple_count + hr_count
            total_at_bats = (df[(df['name'] == name) & (df['position'] == position)]['result']
                             .isin(['一安 Single', '二安 Double', '三安 Triple', '全壘打 Home Run', '外飛 Field Out', '失誤 Field Error', '三振 Strikeout']) 
                             & ~df[(df['name'] == name) & (df['position'] == position)]['result'].isna()).sum()

            if total_at_bats > 0:
                avg = total_hits / total_at_bats
                avg_dict[position][name] = avg
            else:
                avg_dict[position][name] = None

    avg_df = pd.DataFrame(avg_dict)
    avg_df.index.name = 'name'
    return avg_df

# 定義背景更新函數
def refreshData():
    print("\rStart refresh", end="")
    df = pd.read_csv("https://docs.google.com/spreadsheets/d/1n3Xt5iemJ3WWjlksEaU6JfNDv_9FX4CStTzjayMRwEU/export?format=csv&gid=0")
    avg_df = calculate_avg(df)
    avg_df = avg_df.transpose()

    # Get exist image
    existImageDataRequest = requests.get(apiEndpoint + '?n=image&width=2')
    existImageData = existImageDataRequest.json()
    # values = existImageData[1:]
    existImageData = {i[0]: i[1] for i in existImageData}

    unique_names = df['name'].unique()
    new_frames = {}  # everybody's 9 block
    for name in unique_names:
        new_frame = pd.DataFrame(0, index=range(0, 8), columns=range(0, 8), dtype=float)

        # 填充九宮格數據
        for i in range(0, 3):
            for j in range(0, 3):
                try:
                    value = avg_df.loc[3 * i + j + 1, name]
                except KeyError:
                    value = np.nan  # 如果找不到數據，設為 NaN

                new_frame.loc[i * 2 + 1, j * 2 + 1] = value
                new_frame.loc[i * 2 + 1, j * 2 + 2] = value
                new_frame.loc[i * 2 + 2, j * 2 + 1] = value
                new_frame.loc[i * 2 + 2, j * 2 + 2] = value

        # 四角數據填充
        for idx, (positions, label) in enumerate([((0, 0), (1, 0), (2, 0), (3, 0), (0, 1), (0, 2), (0, 3)),  # 左上
                                                  ((0, 4), (0, 5), (0, 6), (0, 7), (1, 7), (2, 7), (3, 7)),  # 右上
                                                  ((4, 0), (5, 0), (6, 0), (7, 0), (7, 1), (7, 2), (7, 3)),  # 左下
                                                  ((7, 4), (7, 5), (7, 6), (7, 7), (6, 7), (5, 7), (4, 7))]):  # 右下
            try:
                value = avg_df.loc[10 + idx, name]
            except KeyError:
                value = np.nan

            for y, x in positions:
                new_frame.loc[y, x] = value

        new_frames[name] = new_frame

    # 生成熱力圖
    for playerName in new_frames:
        plt.clf()
        playerFrame = new_frames[playerName]

        # 使用 seaborn 生成熱力圖
        sns_plot = sns.heatmap(playerFrame, center=0.3, vmin=0, vmax=1, cmap='Blues', square=True, fmt=".3f")
        plt.xticks([])
        plt.yticks([])

        # 動態標註九宮格內的數據
        for i in range(0, 3):
            for j in range(0, 3):
                value = playerFrame.iloc[i * 2 + 1, j * 2 + 1]
                color = 'black' if not pd.isna(value) else 'red'
                value = "%.3f" % value if not pd.isna(value) else 'NO DATA'
                sns_plot.text(j * 2 + 1.5, i * 2 + 1.5, value, ha='center', va='center', color=color)

        # 動態標註四角數據
        for i, j in ((0, 0), (0, 4), (7, 0), (7, 4)):
            value = playerFrame.iloc[i, j]
            color = 'black' if not pd.isna(value) else 'red'
            value = "%.3f" % value if not pd.isna(value) else 'NO DATA'
            sns_plot.text(j + 0.5, i + 0.5, value, ha='center', va='center', color=color)

        # 生成圖像並轉為 Base64
        newImageByts = io.BytesIO()
        plt.savefig(newImageByts, format='png', bbox_inches='tight')
        newImageByts.seek(0)
        newImageBase64 = base64.b64encode(newImageByts.read()).decode()

        # 發送新生成的圖像
        result = None
        if playerName not in existImageData or existImageData[playerName] != newImageBase64:
            result = requests.post(apiEndpoint + '?n=image', json={"key": playerName, "values": [newImageBase64]})
            print()
            print(playerFrame)
            if result.status_code == 200:
                print("Success")
            else:
                print("Error")

        if playerName in existImageData:
            existImageData.pop(playerName)

    # 刪除不存在的球員圖像
    requests.post(apiEndpoint + '?n=image&t=d', json={"key": [i for i in existImageData]})

    plt.close()
    print('\rDone          ', end="")
    
# def refresh_data():
#     try:
#         df = pd.read_csv("https://docs.google.com/spreadsheets/d/1n3Xt5iemJ3WWjlksEaU6JfNDv_9FX4CStTzjayMRwEU/export?format=csv&gid=0")
#         avg_df = calculate_avg(df)
#         avg_df = avg_df.transpose()

#         # Get exist image
#         exist_image_data_request = requests.get(f"http://0.0.0.0:8000/?n=image&width=2")
#         exist_image_data = exist_image_data_request.json()
#         values = exist_image_data[1:]
#         exist_image_data = {i[0]: i[1] for i in values}

#         unique_names = df['name'].unique()
#         new_frames = {}

#         for name in unique_names:
#             new_frame = pd.DataFrame(0, index=range(0, 8), columns=range(0, 8), dtype=float)
#             # Data filling loop (略)
#             new_frames[name] = new_frame

#         for player_name in new_frames:
#             plt.clf()
#             player_frame = new_frames[player_name]
#             sns_plot = sns.heatmap(player_frame, center=0.3, vmin=0, vmax=1, cmap='Blues', square=True, fmt=".3f")
#             plt.xticks([])
#             plt.yticks([])

#             # Create image
#             new_image_bytes = io.BytesIO()
#             plt.savefig(new_image_bytes, format='png', bbox_inches='tight')
#             new_image_bytes.seek(0)
#             new_image_base64 = base64.b64encode(new_image_bytes.read()).decode()

#             # Send image
#             if player_name not in exist_image_data or exist_image_data[player_name] != new_image_base64:
#                 result = requests.post(f"http://0.0.0.0:8000/?n=image", json={
#                     "key": player_name,
#                     "values": [new_image_base64]
#                 })
#                 if result.status_code == 200:
#                     print("Success")
#                 else:
#                     print("Error")

#             if player_name in exist_image_data:
#                 exist_image_data.pop(player_name)

#         # Delete nonexist player
#         requests.post(f"http://0.0.0.0:8000/?n=image&t=d", json={
#             "key": [i for i in exist_image_data],
#         })

#         plt.close()
#         print("Data refresh done.")
#     except Exception as e:
#         print(f"Error refreshing data: {e}")

# API 路由
@app.get("/")
async def get_data(n: str, width: int, background_tasks: BackgroundTasks):
    try:
        worksheet = spreadsheet.worksheet(n)
        values = worksheet.get_all_values()
        truncated_values = [row[:width] for row in values[1:]]

        # # 在讀取資料時觸發更新
        # background_tasks.add_task(refresh_data)

        return JSONResponse(content=truncated_values)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/")
async def post_data(request: Request, background_tasks: BackgroundTasks, n: str, t: str = "w"):
    try:
        worksheet = spreadsheet.worksheet(n)
        data = await request.json()
        
        if t == 'a':
            keys = worksheet.row_values(1)
            values = [''] * len(keys)
            for item in data:
                index = keys.index(item['name']) if item['name'] in keys else -1
                if index != -1:
                    values[index] = item['value']
            worksheet.append_row(values)
        
        elif t == 'w':
            keys = worksheet.col_values(1)
            request_key = data['key']
            row_index = keys.index(request_key) + 1 if request_key in keys else len(keys) + 1
            worksheet.update_cell(row_index, 1, request_key)
            for i, value in enumerate(data['values'], start=2):
                worksheet.update_cell(row_index, i, value)
        
        elif t == 'd':
            keys = worksheet.col_values(1)
            request_keys = data['key']
            for key in request_keys:
                try:
                    row = keys.index(key) + 1
                    worksheet.delete_row(row)
                    keys.pop(row - 1)
                except ValueError:
                    continue
        else:
            raise HTTPException(status_code=400, detail="Invalid type parameter")

        # 在每次資料變動時觸發更新
        background_tasks.add_task(refresh_data)
        
        return JSONResponse(content={})
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


#if time doesn't sync, > ntpdate time.google.com
#uvicorn backend:app --host 0.0.0.0 --port 8000
