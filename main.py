"""
FastAPI To-Do List API
A simple and efficient API for managing tasks
Author: Gabriel Demetrios Lafis
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

app = FastAPI(
    title="To-Do List API",
    description="A simple and efficient API for managing your tasks",
    version="1.0.0",
    contact={
        "name": "Gabriel Demetrios Lafis",
        "url": "https://github.com/gabriellafis",
    }
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    description: Optional[str] = Field(None, max_length=1000, description="Task description")
    completed: bool = Field(default=False, description="Task completion status")
    priority: Optional[str] = Field(default="medium", pattern="^(low|medium|high)$", description="Task priority level")

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    completed: Optional[bool] = None
    priority: Optional[str] = Field(None, pattern="^(low|medium|high)$")

class Task(TaskBase):
    id: str = Field(..., description="Unique task identifier")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: datetime = Field(..., description="Task last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Complete FastAPI project",
                "description": "Build a complete CRUD API with FastAPI",
                "completed": False,
                "priority": "high",
                "created_at": "2025-10-01T10:00:00",
                "updated_at": "2025-10-01T10:00:00"
            }
        }

# In-memory database
tasks_db: dict[str, Task] = {}

# Routes
@app.get("/", tags=["Root"])
async def root():
    """Welcome endpoint"""
    return {
        "message": "Welcome to To-Do List API",
        "version": "1.0.0",
        "documentation": "/docs",
        "author": "Gabriel Demetrios Lafis"
    }

@app.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED, tags=["Tasks"])
async def create_task(task: TaskCreate):
    """
    Create a new task
    
    - **title**: Task title (required)
    - **description**: Task description (optional)
    - **completed**: Completion status (default: false)
    - **priority**: Priority level - low, medium, or high (default: medium)
    """
    task_id = str(uuid.uuid4())
    now = datetime.now()
    
    new_task = Task(
        id=task_id,
        title=task.title,
        description=task.description,
        completed=task.completed,
        priority=task.priority,
        created_at=now,
        updated_at=now
    )
    
    tasks_db[task_id] = new_task
    return new_task

@app.get("/tasks", response_model=List[Task], tags=["Tasks"])
async def list_tasks(
    completed: Optional[bool] = None,
    priority: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    """
    List all tasks with optional filters
    
    - **completed**: Filter by completion status (optional)
    - **priority**: Filter by priority level (optional)
    - **skip**: Number of tasks to skip (pagination)
    - **limit**: Maximum number of tasks to return
    """
    tasks = list(tasks_db.values())
    
    # Apply filters
    if completed is not None:
        tasks = [task for task in tasks if task.completed == completed]
    
    if priority is not None:
        tasks = [task for task in tasks if task.priority == priority]
    
    # Sort by creation date (newest first)
    tasks.sort(key=lambda x: x.created_at, reverse=True)
    
    # Apply pagination
    return tasks[skip:skip + limit]

@app.get("/tasks/{task_id}", response_model=Task, tags=["Tasks"])
async def get_task(task_id: str):
    """
    Get a specific task by ID
    
    - **task_id**: Unique task identifier
    """
    if task_id not in tasks_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id '{task_id}' not found"
        )
    
    return tasks_db[task_id]

@app.put("/tasks/{task_id}", response_model=Task, tags=["Tasks"])
async def update_task(task_id: str, task_update: TaskUpdate):
    """
    Update an existing task
    
    - **task_id**: Unique task identifier
    - **title**: New task title (optional)
    - **description**: New task description (optional)
    - **completed**: New completion status (optional)
    - **priority**: New priority level (optional)
    """
    if task_id not in tasks_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id '{task_id}' not found"
        )
    
    existing_task = tasks_db[task_id]
    update_data = task_update.model_dump(exclude_unset=True)
    
    # Update only provided fields
    for field, value in update_data.items():
        setattr(existing_task, field, value)
    
    existing_task.updated_at = datetime.now()
    tasks_db[task_id] = existing_task
    
    return existing_task

@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Tasks"])
async def delete_task(task_id: str):
    """
    Delete a task
    
    - **task_id**: Unique task identifier
    """
    if task_id not in tasks_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id '{task_id}' not found"
        )
    
    del tasks_db[task_id]
    return None

@app.get("/tasks/stats/summary", tags=["Statistics"])
async def get_stats():
    """
    Get statistics about tasks
    
    Returns total, completed, pending tasks and breakdown by priority
    """
    total = len(tasks_db)
    completed = sum(1 for task in tasks_db.values() if task.completed)
    pending = total - completed
    
    priority_stats = {
        "low": sum(1 for task in tasks_db.values() if task.priority == "low"),
        "medium": sum(1 for task in tasks_db.values() if task.priority == "medium"),
        "high": sum(1 for task in tasks_db.values() if task.priority == "high")
    }
    
    return {
        "total_tasks": total,
        "completed_tasks": completed,
        "pending_tasks": pending,
        "completion_rate": round((completed / total * 100), 2) if total > 0 else 0,
        "priority_breakdown": priority_stats
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
