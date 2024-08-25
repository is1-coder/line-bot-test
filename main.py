from fastapi import FastAPI, Request, BackgroundTasks, Header, HTTPException
from dotenv import load_dotenv
import os, requests
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextSendMessage
from pydantic import BaseModel, Field

app = FastAPI(
    title="LINEBOT-API-TALK-A3RT",
    description="LINEBOT-API-TALK-A3RT by FastAPI.",
    version="1.0",
)

# ApiRoot Health Check
@app.get("/")
def api_root():
    return {"message": "LINEBOT-API-TALK-A3RT Healthy!"}

# 環境変数の追加
load_dotenv()

# LINE Messaging APIの準備
line_bot_api = LineBotApi(os.environ["CHANNEL_ACCESS_TOKEN"])
handler = WebhookHandler(os.environ["CHANNEL_SECRET"])

# A3RT APIの準備
A3RT_TALKAPI_KEY = os.environ["A3RT_TALKAPI_KEY"]
A3RT_TALKAPI_URL = os.environ["A3RT_TALKAPI_URL"]

# A3RT APIに送信するメッセージのクラスを定義
class Question(BaseModel):
    query: str = Field(description="メッセージ")

# LINE Messaging APIからのリクエストを非同期で処理
@app.post("/callback")
async def callback(
    request: Request,
    background_tasks: BackgroundTasks,
    x_line_signature=Header(None), # リクエストのヘッダーから x_line_signature を取得、存在しない場合Noneを代入
    summary="LINE Message APIからのコールバックです。"  # 自動生成されるエンドポイントのドキュメントページで使用される
):
    body = await request.body()
    try:
        # 非同期で実行する処理を指定
        background_tasks.add_task(
            handler.handle, body.decode("utf-8"), x_line_signature
        )
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    return "ok"


# LINE Messaging APIからのメッセージイベントを処理
@handler.add(MessageEvent)
def handle_message(event):
    if event.type != "message" or event.message.type != "text":
        return
    ai_message = talk(Question(query=event.message.text))
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ai_message))

# A3RT API とやり取り
@app.post("/talk")  # line messaging api以外からのリクエストがない場合、このエンドポイントは不要?
def talk(question: Question) -> str:
    """ A3RT Talk API
    https://a3rt.recruit.co.jp/product/talkAPI/
    """
    # A3RT APIにpostリクエストを送信、レスポンスをjsonに変換
    replay_message = requests.post(
        A3RT_TALKAPI_URL,
        {"apikey": A3RT_TALKAPI_KEY, "query": question.query},
        timeout=5,
    ).json()
    if replay_message["status"] != 0:
        if replay_message["message"] == "empty reply":
            return "ちょっとわかりません"
        else:
            return replay_message["message"]
    return replay_message["results"][0]["reply"]


# Run application
if __name__ == "__main__":
    app.run()

