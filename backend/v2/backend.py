from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import gspread
from google.oauth2.service_account import Credentials
import json

app = FastAPI()

# 設定 Google Sheets API 的範圍
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# 加載服務帳戶憑證
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
client = gspread.authorize(creds)

# 打開你的 Google Sheets
spreadsheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1n3Xt5iemJ3WWjlksEaU6JfNDv_9FX4CStTzjayMRwEU/edit#gid=0")

@app.get("/")
async def get_data(n: str, width: int):
    try:
        worksheet = spreadsheet.worksheet(n)
        values = worksheet.get_all_values()
        # 根據 width 截取每行的前 width 個值
        truncated_values = [row[:width] for row in values]
        return JSONResponse(content=truncated_values)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/")
async def post_data(n: str, t: str = "w", request: Request):
    try:
        worksheet = spreadsheet.worksheet(n)
        data = await request.json()
        
        if t == 'a':
            # Append
            keys = worksheet.row_values(1)
            values = [''] * len(keys)
            for item in data:
                index = keys.index(item['name']) if item['name'] in keys else -1
                if index != -1:
                    values[index] = item['value']
            worksheet.append_row(values)
        
        elif t == 'w':
            # Write
            keys = worksheet.col_values(1)
            request_key = data['key']
            row_index = keys.index(request_key) + 1 if request_key in keys else len(keys) + 1
            worksheet.update_cell(row_index, 1, request_key)
            # 假設 data['values'] 是一個列表
            for i, value in enumerate(data['values'], start=2):
                worksheet.update_cell(row_index, i, value)
        
        elif t == 'd':
            # Delete
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
        
        return JSONResponse(content={})
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
