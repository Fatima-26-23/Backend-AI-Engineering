from fastapi import FastAPI, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()


# Request Models
class TaskCreate(BaseModel):
    title: str


class TaskUpdate(BaseModel):
    title: str
    done: bool


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


# Health endpoint
@app.get("/health")
async def health():
    return {
        "status": "ok"
    }


# Get all tasks
@app.get("/tasks")
async def get_tasks():
    return tasks


# Get a single task
@app.get("/tasks/{id}")
async def get_task(id: int):
    for task in tasks:
        if task["id"] == id:
            return task

    return JSONResponse(
        status_code=404,
        content={"error": f"Task {id} not found"}
    )


# Create a new task
@app.post("/tasks", status_code=status.HTTP_201_CREATED)
async def create_task(task: TaskCreate):

    if not task.title.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "Title cannot be empty"}
        )

    new_task = {
        "id": len(tasks) + 1,
        "title": task.title,
        "done": False
    }

    tasks.append(new_task)

    return new_task


# Update a task
@app.put("/tasks/{id}")
async def update_task(id: int, updated_task: TaskUpdate):

    if not updated_task.title.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "Title cannot be empty"}
        )

    for task in tasks:
        if task["id"] == id:
            task["title"] = updated_task.title
            task["done"] = updated_task.done
            return task

    return JSONResponse(
        status_code=404,
        content={"error": f"Task {id} not found"}
    )


# Delete a task
@app.delete("/tasks/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(id: int):

    for task in tasks:
        if task["id"] == id:
            tasks.remove(task)
            return Response(status_code=status.HTTP_204_NO_CONTENT)

    return JSONResponse(
        status_code=404,
        content={"error": f"Task {id} not found"}
    )