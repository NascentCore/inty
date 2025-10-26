from pydantic import BaseModel, Field


class StartTaskRequest(BaseModel):
    device_token: str = Field(min_length=10)
    task_name: str = Field(default="demo_task")
    duration_seconds: int = Field(default=5, ge=0, le=3600)


class StartTaskResponse(BaseModel):
    task_id: str
    status: str


class NotifyRequest(BaseModel):
    device_token: str = Field(min_length=10)
    title: str = Field(default="任务完成")
    body: str = Field(default="服务器端任务已完成")
    data: dict = Field(default_factory=dict)


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    task_name: str
    duration_seconds: int
