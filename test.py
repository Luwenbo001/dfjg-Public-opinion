# 示例1：基础计算器服务器
from fastmcp import MCPServer, Request
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
mcp_server = MCPServer(app)

class CalculationRequest(BaseModel):
    x: float
    y: float

@mcp_server.mcp_endpoint
async def add(request: Request[CalculationRequest]) -> float:
    """将两个数字相加"""
    data = request.params
    return data.x + data.y

@mcp_server.mcp_endpoint
async def subtract(request: Request[CalculationRequest]) -> float:
    """从第一个数字中减去第二个数字"""
    data = request.params
    return data.x - data.y

@mcp_server.mcp_endpoint
async def multiply(request: Request[CalculationRequest]) -> float:
    """将两个数字相乘"""
    data = request.params
    return data.x * data.y

@mcp_server.mcp_endpoint
async def divide(request: Request[CalculationRequest]) -> float:
    """将第一个数字除以第二个数字"""
    data = request.params
    if data.y == 0:
        raise ValueError("除数不能为零")
    return data.x / data.y

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


# 示例2：天气信息服务器
from fastmcp import MCPServer, Request
from fastapi import FastAPI
from pydantic import BaseModel
import random
from datetime import datetime, timedelta

app = FastAPI()
mcp_server = MCPServer(app)

class WeatherRequest(BaseModel):
    city: str
    days: int = 1

class WeatherInfo(BaseModel):
    date: str
    temperature: float
    condition: str
    humidity: int

@mcp_server.mcp_endpoint
async def get_weather(request: Request[WeatherRequest]) -> list[WeatherInfo]:
    """获取指定城市的天气预报"""
    data = request.params
    
    # 这里使用模拟数据，实际应用中会调用真实的天气API
    weather_conditions = ["晴朗", "多云", "小雨", "大雨", "雷雨", "小雪"]
    
    result = []
    today = datetime.now()
    
    for i in range(data.days):
        date = today + timedelta(days=i)
        result.append(WeatherInfo(
            date=date.strftime("%Y-%m-%d"),
            temperature=round(random.uniform(15, 30), 1),
            condition=random.choice(weather_conditions),
            humidity=random.randint(30, 90)
        ))
    
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)


# 示例3：文件操作服务器
from fastmcp import MCPServer, Request
from fastapi import FastAPI
from pydantic import BaseModel
import os
import json

app = FastAPI()
mcp_server = MCPServer(app)

# 模拟文件系统（实际应用中使用真实文件系统）
file_system = {}

class FileWriteRequest(BaseModel):
    filename: str
    content: str

class FileReadRequest(BaseModel):
    filename: str

class FileListRequest(BaseModel):
    directory: str = "/"

class FileDeleteRequest(BaseModel):
    filename: str

@mcp_server.mcp_endpoint
async def write_file(request: Request[FileWriteRequest]) -> bool:
    """将内容写入文件"""
    data = request.params
    file_system[data.filename] = data.content
    return True

@mcp_server.mcp_endpoint
async def read_file(request: Request[FileReadRequest]) -> str:
    """读取文件内容"""
    data = request.params
    if data.filename not in file_system:
        raise ValueError(f"文件 {data.filename} 不存在")
    return file_system[data.filename]

@mcp_server.mcp_endpoint
async def list_files(request: Request[FileListRequest]) -> list[str]:
    """列出指定目录中的文件"""
    return list(file_system.keys())

@mcp_server.mcp_endpoint
async def delete_file(request: Request[FileDeleteRequest]) -> bool:
    """删除文件"""
    data = request.params
    if data.filename not in file_system:
        raise ValueError(f"文件 {data.filename} 不存在")
    del file_system[data.filename]
    return True

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)


# 示例4：综合应用 - 个人助手服务
from fastmcp import MCPServer, Request
from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import json
import random

app = FastAPI()
mcp_server = MCPServer(app)

# 模拟数据存储
notes_db = []
todos_db = []
contacts_db = []

class Note(BaseModel):
    id: int = None
    title: str
    content: str
    created_at: str = None

class Todo(BaseModel):
    id: int = None
    task: str
    completed: bool = False
    due_date: str = None

class Contact(BaseModel):
    id: int = None
    name: str
    phone: str
    email: str = None

class SearchRequest(BaseModel):
    query: str

@mcp_server.mcp_endpoint
async def add_note(request: Request[Note]) -> Note:
    """添加一条笔记"""
    note = request.params
    note.id = len(notes_db) + 1
    note.created_at = datetime.now().isoformat()
    notes_db.append(note)
    return note

@mcp_server.mcp_endpoint
async def get_notes(request: Request) -> list[Note]:
    """获取所有笔记"""
    return notes_db

@mcp_server.mcp_endpoint
async def add_todo(request: Request[Todo]) -> Todo:
    """添加一个待办事项"""
    todo = request.params
    todo.id = len(todos_db) + 1
    if not todo.due_date:
        todo.due_date = (datetime.now() + timedelta(days=1)).isoformat()
    todos_db.append(todo)
    return todo

@mcp_server.mcp_endpoint
async def get_todos(request: Request) -> list[Todo]:
    """获取所有待办事项"""
    return todos_db

@mcp_server.mcp_endpoint
async def complete_todo(request: Request[int]) -> Todo:
    """标记待办事项为已完成"""
    todo_id = request.params
    for todo in todos_db:
        if todo.id == todo_id:
            todo.completed = True
            return todo
    raise ValueError(f"待办事项 #{todo_id} 不存在")

@mcp_server.mcp_endpoint
async def add_contact(request: Request[Contact]) -> Contact:
    """添加联系人"""
    contact = request.params
    contact.id = len(contacts_db) + 1
    contacts_db.append(contact)
    return contact

@mcp_server.mcp_endpoint
async def get_contacts(request: Request) -> list[Contact]:
    """获取所有联系人"""
    return contacts_db

@mcp_server.mcp_endpoint
async def search(request: Request[SearchRequest]) -> dict:
    """搜索笔记、待办事项和联系人"""
    query = request.params.query.lower()
    
    matching_notes = [note for note in notes_db if query in note.title.lower() or query in note.content.lower()]
    matching_todos = [todo for todo in todos_db if query in todo.task.lower()]
    matching_contacts = [contact for contact in contacts_db if query in contact.name.lower()]
    
    return {
        "notes": matching_notes,
        "todos": matching_todos,
        "contacts": matching_contacts
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)

