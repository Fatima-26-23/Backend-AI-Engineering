from fastapi import FastAPI, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from database import conn, cursor

app = FastAPI()


# Request Models
class TaskCreate(BaseModel):
    title: str


class TaskUpdate(BaseModel):
    title: str
    done: bool


# Root endpoint
@app.get(
    "/",
    summary="API Information",
    description="Returns basic information about the Task API."
)
async def root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"]
    }


# Health endpoint
@app.get(
    "/health",
    summary="Health Check",
    description="Checks whether the API is running."
)
async def health():
    return {
        "status": "ok"
    }


# Get all tasks
@app.get(
    "/tasks",
    summary="Get All Tasks",
    description="Returns the complete list of tasks."
)
async def get_tasks():

    cursor.execute("SELECT * FROM tasks")
    rows = cursor.fetchall()

    tasks = []

    for row in rows:
        tasks.append({
            "id": row[0],
            "title": row[1],
            "done": bool(row[2])
        })

    return tasks


# Get a single task
@app.get(
    "/tasks/{id}",
    summary="Get Task by ID",
    description="Returns a single task using its ID."
)
async def get_task(id: int):

    cursor.execute(
        "SELECT * FROM tasks WHERE id = ?",
        (id,)
    )

    row = cursor.fetchone()

    if row is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {id} not found"}
        )

    return {
        "id": row[0],
        "title": row[1],
        "done": bool(row[2])
    }


# Create a new task
@app.post(
    "/tasks",
    status_code=status.HTTP_201_CREATED,
    summary="Create Task",
    description="Creates a new task."
)
async def create_task(task: TaskCreate):

    if not task.title.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "Title cannot be empty"}
        )

    cursor.execute(
        "INSERT INTO tasks (title, done) VALUES (?, ?)",
        (task.title, False)
    )

    conn.commit()

    new_id = cursor.lastrowid

    return {
        "id": new_id,
        "title": task.title,
        "done": False
    }


# Update a task
@app.put(
    "/tasks/{id}",
    summary="Update Task",
    description="Updates the title and completion status of a task."
)
async def update_task(id: int, updated_task: TaskUpdate):

    if not updated_task.title.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "Title cannot be empty"}
        )

    cursor.execute(
        """
        UPDATE tasks
        SET title = ?, done = ?
        WHERE id = ?
        """,
        (updated_task.title, updated_task.done, id)
    )

    conn.commit()

    if cursor.rowcount == 0:
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {id} not found"}
        )

    return {
        "id": id,
        "title": updated_task.title,
        "done": updated_task.done
    }


# Delete a task
@app.delete(
    "/tasks/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Task",
    description="Deletes a task using its ID."
)
async def delete_task(id: int):

    cursor.execute(
        "DELETE FROM tasks WHERE id = ?",
        (id,)
    )

    conn.commit()

    if cursor.rowcount == 0:
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {id} not found"}
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)