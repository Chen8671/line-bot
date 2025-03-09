import sqlite3
import yfinance as yf
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# 初始化 Flask 應用
app = Flask(__name__)

# 使用硬編碼方式設置 LINE Bot 的 Access Token 和 Channel Secret
line_bot_api = LineBotApi('D9zBfnRl2A6H/Vvj+DH0CpyBLIjdLYHmgsVI+ndsHssd+dwUwy5gtyw3rvx4Cg4X0skcPSeGrb7YIYWkLmrxAzUWBG6uQ2HJtb1gayfIHkFcDjLxdDb+pxLbLc//i9xc/IsKnDXUAp1MMurIq3gmqQdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('5b750f8f51ea241fe0a6579fdcf61ed5')

# SQLite 數據庫文件路徑
DB_FILE_PATH = 'stocks_data.db'

# 初始化 SQLite 數據庫
def initialize_database():
    conn = sqlite3.connect(DB_FILE_PATH)
    c = conn.cursor()
    # 創建 stocks 表
    c.execute('''
    CREATE TABLE IF NOT EXISTS stocks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        ticker TEXT NOT NULL, 
        company_name TEXT, 
        valuation REAL, 
        risk REAL, 
        date TEXT NOT NULL
    )
    ''')
    conn.commit()
    conn.close()
    print("SQLite 資料庫初始化完成，表 'stocks' 已創建。")

# 查詢並保存股票健康狀況的函式
def get_stock_health(stock_code):
    try:
        stock = yf.Ticker(stock_code)  # 使用 yfinance 取得股票資訊
        if stock.info and 'symbol' in stock.info:  # 確保股票資訊非空
            ticker = stock_code
            company_name = stock.info.get('longName', 'N/A')
            valuation = stock.info.get('forwardPE', 'N/A')  # 取得估值（前瞻市盈率）
            risk = stock.info.get('beta', 'N/A')  # 風險評估（Beta 值）
            
            # 保存數據到資料庫
            save_to_database(ticker, company_name, valuation, risk)

            return (f"股票代號 {ticker} 的健康狀況：\n"
                    f"公司名稱：{company_name}\n"
                    f"估值（前瞻市盈率）：{valuation}\n"
                    f"風險評估（Beta）：{risk}")
        else:
            return "無法獲取股票健康資料，請檢查股票代號是否正確。"
    except Exception as e:
        return f"查詢股票時發生錯誤：{str(e)}"

# 將股票資訊保存到 SQLite 資料庫
def save_to_database(ticker, company_name, valuation, risk):
    try:
        conn = sqlite3.connect(DB_FILE_PATH)
        cursor = conn.cursor()
        # 插入股票資料
        cursor.execute('''
        INSERT INTO stocks (ticker, company_name, valuation, risk, date)
        VALUES (?, ?, ?, ?, CURRENT_DATE)
        ''', (ticker, company_name, valuation, risk))
        
        conn.commit()
        conn.close()
        print(f"股票代號 {ticker} 的數據已成功保存到資料庫。")
    except Exception as e:
        print(f"保存股票資訊時發生錯誤：{str(e)}")

# Line Bot 的 Webhook 處理
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')  # 從請求頭中取得簽名
    body = request.get_data(as_text=True)  # 取得請求內容
    try:
        handler.handle(body, signature)  # 使用 WebhookHandler 驗證和處理
    except InvalidSignatureError:  # 如果簽名無效，返回錯誤
        print("無效的簽名錯誤")
        abort(400)
    except Exception as e:
        print(f"處理回調時發生錯誤：{str(e)}")
        abort(500)
    return 'OK'

# 處理使用者發送的文字訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_input = event.message.text.strip()  # 取得使用者輸入的訊息

    # 判斷是否為股票代號
    if user_input.isdigit() or "." in user_input:
        # 如果是純數字，為台灣股票自動添加市場代碼
        if "." not in user_input:
            user_input += ".TW"  # 默認添加台灣市場代碼
        result = get_stock_health(user_input)  # 查詢股票健康資料
    else:
        result = "無效的股票代號，請輸入正確的股票代號（例如：2330 或 AAPL）。"

    # 回應結果
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=result))

# 啟動應用程式
if __name__ == '__main__':
    initialize_database()  # 初始化資料庫
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))  # 設置執行的主機及埠號
