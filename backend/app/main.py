from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import posts, insights, feed, market, users, admin, trends, transparency


app = FastAPI(title="Social Stocks Insights API")

# Configure CORS
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def healthcheck():
    return {"status": "ok"}


app.include_router(posts.router, prefix="/posts", tags=["posts"])
app.include_router(insights.router, prefix="/insights", tags=["insights"])
app.include_router(feed.router, prefix="/feed", tags=["feed"])
app.include_router(market.router, prefix="/market", tags=["market"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(trends.router, prefix="/trends", tags=["trends"])
app.include_router(transparency.router, prefix="/transparency", tags=["transparency"])
