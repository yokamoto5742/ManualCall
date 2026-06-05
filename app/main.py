"""FastAPIアプリ初期化・ルーター登録（§2.4）"""

from fastapi import FastAPI

from app.routers import media_stream, twiml

app = FastAPI(title="EyeManual", description="眼科業務マニュアル応対AIボット")

app.include_router(twiml.router)
app.include_router(media_stream.router)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
