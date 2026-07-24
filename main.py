from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

# In-memory list of tasks
tasks = [
    {"id": 1, "title": "Buy groceries", "done": False},
    {"id": 2, "title": "Complete assignment", "done": True},
    {"id": 3, "title": "Go for a walk", "done": False},
]


# Root endpoint
@app.get("/")
async def root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"]
    }


# Health check endpoint
@app.get("/health")
async def health():
    return {
        "status": "ok"
    }


# Get all tasks
@app.get("/tasks")
async def get_tasks():
    return tasks


# Get a single task by ID
@app.get("/tasks/{id}")
async def get_task(id: int):
    for task in tasks:
        if task["id"] == id:
            return task

    return JSONResponse(
        status_code=404,
        content={"error": f"Task {id} not found"}
    )