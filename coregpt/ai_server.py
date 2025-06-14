from fastapi import FastAPI, Request
import uvicorn

app = FastAPI()

@app.post("/api/generate")
async def generate(request: Request):
    data = await request.json()
    inputs = data.get("inputs")
    if not inputs or not isinstance(inputs, list):
        return {"error": "inputs must be a non-empty list"}

    prompt = inputs[0]
    # Fake response, just echoes back prompt with a note.
    # Replace this with real AI calls when ready.
    return {"results": [{"text": f"Echo: {prompt}"}]}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=52653)
