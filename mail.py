import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# .envファイルを読み込む
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

# データベース接続設定
DB_USER = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DATABASE_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# SQLAlchemy Engineを作成
engine = create_engine(DATABASE_URL)

# FastAPIアプリケーションの初期化
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gmail認証情報（適切な値に置き換えてください）
SMTP_USER = "kosukekunii4@gmail.com"
SMTP_PASSWORD = "spdigoeovzfuvuur"

class EmailData(BaseModel):
    user_id: int
    recommend_ids: list[int]

@app.post("/send-recommendation-email")
async def send_recommendation_email(email_data: EmailData):

    user_id = email_data.user_id
    recommend_ids = email_data.recommend_ids

    with engine.connect() as connection:
        user_result = connection.execute(text("SELECT email FROM Users WHERE user_id = :user_id"), {"user_id": user_id}).fetchone()
        if user_result is None:
            raise HTTPException(status_code=404, detail="User not found")

        user_mail = user_result.email

        content_info_list = []
        for recommend_id in recommend_ids:
            content_result = connection.execute(text("SELECT title, url FROM Content WHERE content_id = :recommend_id"), {"recommend_id": recommend_id}).fetchall()
            content_info_list.extend(content_result)

    # メール本文を作成
    mail_body = "<h1>おすすめのコンテンツ</h1>"
    for content in content_info_list:
        mail_body += f"<p>{content[0]} - <a href='{content[1]}'>{content[1]}</a></p>"

    # MIMEMultipartオブジェクトの作成
    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = user_mail  # ユーザーのメールアドレス
    msg['Subject'] = "おすすめコンテンツ"
    msg.attach(MIMEText(mail_body, 'html'))

    result = send_gmail(msg)

    if result:
        return JSONResponse(content={"message": "Email sent successfully"}, status_code=200)
    else:
        return JSONResponse(content={"message": "Failed to send email"}, status_code=500)

def send_gmail(msg):
    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context())
        server.set_debuglevel(0)
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("メール送信成功")
        return True
    except Exception as e:
        print(f"メール送信失敗: {e}")
        return False
