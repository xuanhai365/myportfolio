from fastapi import FastAPI, UploadFile
import uvicorn
from model.inference import billsOCR

app = FastAPI()
model = billsOCR()
# Define API endpoints
@app.post("/infer")
async def infer(image: UploadFile):
    image_data = await image.read()
    # Prediction logic (partial)
    predictions = model.inference(image_data, output='./output')
    return {'result': predictions}
@app.get("/health")
async def health():
    return {"message": "ok"}
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)