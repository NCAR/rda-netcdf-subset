from fastapi import FastAPI
import routes.endpoints as endpoints

app = FastAPI()

app.include_router(endpoints.router)