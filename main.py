from fastapi import FastAPI, Depends, HTTPException, status, Request, Form, Response, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, timezone
from ai_client import generate_chat_response
from database import engine, get_db
import models
from sqlalchemy.orm import Session
import uuid
import hashlib
import json
import base64
import mimetypes
from passlib.context import CryptContext
from jose import jwt, JWTError
import config

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Buddy Chat")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

COOKIE_OPTS = {
    "httponly": True,
    "samesite": "lax",
    "max_age": config.ACCESS_TOKEN_EXPIRE_DAYS * 86400,
}


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=config.ACCESS_TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": username, "exp": expire},
        config.SECRET_KEY,
        algorithm=config.ALGORITHM,
    )


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(key="session_token", value=token, **COOKIE_OPTS)


class ChatRequest(BaseModel):
    chat_id: str
    messages: List[Dict[str, Any]]
    title: Optional[str] = None
    project_id: Optional[str] = None
    is_temporary: Optional[bool] = False
    max_tokens: Optional[int] = Field(default=4000, ge=256, le=16000)
    temperature: Optional[float] = Field(default=0.7, ge=0, le=2)


class ChatSessionCreate(BaseModel):
    id: str
    title: str
    messages: list
    total_tokens: int
    token_limit: int
    locked_until: int
    project_id: Optional[str] = None


class UserUpdate(BaseModel):
    display_name: str
    password: Optional[str] = None


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: str
    description: Optional[str] = None


class WebSearchRequest(BaseModel):
    query: str


class FileUploadResponse(BaseModel):
    filename: str
    file_type: str
    size: int
    content: str
    is_image: bool


def get_current_user_obj(request: Request, db: Session):
    token = request.cookies.get("session_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            return None
    except JWTError:
        return None
    return db.query(models.User).filter(models.User.username == username).first()


def require_user(request: Request, db: Session):
    user = get_current_user_obj(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user


def get_query_hash(user_id: str, messages: list) -> str:
    payload = {"user_id": user_id, "messages": messages}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_obj(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    display_name = user.display_name or user.username
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"user": user.username, "display_name": display_name},
    )


@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request, db: Session = Depends(get_db)):
    if get_current_user_obj(request, db):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="login.html")


@app.post("/login")
async def login_post(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return RedirectResponse(url="/login?error=1", status_code=status.HTTP_302_FOUND)

    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    set_session_cookie(response, create_access_token(user.username))
    return response


@app.get("/register", response_class=HTMLResponse)
async def register_get(request: Request, db: Session = Depends(get_db)):
    if get_current_user_obj(request, db):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="register.html")


@app.post("/register")
async def register_post(
    username: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(...),
    db: Session = Depends(get_db),
):
    if len(username.strip()) < 3:
        return RedirectResponse(url="/register?error=short", status_code=status.HTTP_302_FOUND)
    if len(password) < 6:
        return RedirectResponse(url="/register?error=password", status_code=status.HTTP_302_FOUND)

    if db.query(models.User).filter(models.User.username == username).first():
        return RedirectResponse(url="/register?error=exists", status_code=status.HTTP_302_FOUND)

    new_user = models.User(
        id=str(uuid.uuid4()),
        username=username.strip(),
        display_name=display_name.strip() or username.strip(),
        hashed_password=get_password_hash(password),
    )
    db.add(new_user)
    db.commit()

    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    set_session_cookie(response, create_access_token(username))
    return response


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("session_token")
    return response


@app.post("/api/user/update")
async def update_user(request: Request, data: UserUpdate, db: Session = Depends(get_db)):
    user = require_user(request, db)
    user.display_name = data.display_name.strip() or user.username
    if data.password:
        if len(data.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        user.hashed_password = get_password_hash(data.password)
    db.commit()
    return {"status": "success", "display_name": user.display_name}


@app.post("/api/chat")
async def chat_api(request: Request, chat_req: ChatRequest, db_session: Session = Depends(get_db)):
    user = require_user(request, db_session)

    chat = db_session.query(models.ChatSession).filter(
        models.ChatSession.id == chat_req.chat_id,
        models.ChatSession.user_id == user.id,
    ).first()

    has_images = any(
        isinstance(m.get("content"), str) and "[IMAGE:" in m.get("content", "")
        for m in chat_req.messages
    )

    cached = None
    if not has_images and not chat_req.is_temporary:
        q_hash = get_query_hash(user.id, chat_req.messages)
        cached = db_session.query(models.GlobalCache).filter(
            models.GlobalCache.query_hash == q_hash
        ).first()
        if cached and cached.created_at:
            age = datetime.utcnow() - cached.created_at
            if age.total_seconds() > 86400:
                db_session.delete(cached)
                db_session.flush()
                cached = None

    if cached:
        result = {"reply": cached.response_text, "total_tokens": cached.total_tokens}
    else:
        result = await generate_chat_response(
            chat_req.messages,
            max_tokens=chat_req.max_tokens,
            temperature=chat_req.temperature,
        )
        if not has_images and not chat_req.is_temporary:
            q_hash = get_query_hash(user.id, chat_req.messages)
            db_session.merge(
                models.GlobalCache(
                    query_hash=q_hash,
                    response_text=result["reply"],
                    total_tokens=result["total_tokens"],
                )
            )

    if chat_req.is_temporary:
        return {
            "message": result["reply"],
            "total_tokens": result["total_tokens"],
            "token_limit": 1000,
            "locked_until": 0,
        }

    if not chat:
        title = chat_req.title or "New Chat"
        chat = models.ChatSession(
            id=chat_req.chat_id,
            user_id=user.id,
            project_id=chat_req.project_id,
            title=title,
            messages=chat_req.messages,
        )
        db_session.add(chat)
    elif chat_req.project_id is not None:
        chat.project_id = chat_req.project_id

    chat.total_tokens = result["total_tokens"]
    chat.messages = chat_req.messages + [{"role": "assistant", "content": result["reply"]}]
    chat.updated_at = datetime.utcnow()
    if chat_req.title:
        chat.title = chat_req.title
    db_session.commit()

    return {
        "message": result["reply"],
        "total_tokens": result["total_tokens"],
        "token_limit": chat.token_limit,
        "locked_until": chat.locked_until,
    }


@app.get("/api/chats")
def get_chats(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    return (
        db.query(models.ChatSession)
        .filter(models.ChatSession.user_id == user.id)
        .order_by(models.ChatSession.updated_at.desc())
        .all()
    )


@app.post("/api/chats")
def save_chat_state(request: Request, state: ChatSessionCreate, db: Session = Depends(get_db)):
    user = require_user(request, db)
    chat = db.query(models.ChatSession).filter(
        models.ChatSession.id == state.id,
        models.ChatSession.user_id == user.id,
    ).first()

    if not chat:
        chat = models.ChatSession(id=state.id, user_id=user.id, project_id=state.project_id)
        db.add(chat)

    chat.title = state.title
    chat.messages = state.messages
    chat.total_tokens = state.total_tokens
    chat.token_limit = state.token_limit
    chat.locked_until = state.locked_until
    if state.project_id is not None:
        chat.project_id = state.project_id
    chat.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "ok"}


@app.delete("/api/chats/{chat_id}")
async def delete_chat(request: Request, chat_id: str, db: Session = Depends(get_db)):
    user = require_user(request, db)
    chat = db.query(models.ChatSession).filter(
        models.ChatSession.id == chat_id,
        models.ChatSession.user_id == user.id,
    ).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    db.delete(chat)
    db.commit()
    return {"status": "success"}


@app.get("/api/projects")
async def get_projects(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    return db.query(models.Project).filter(models.Project.user_id == user.id).all()


@app.post("/api/projects")
async def create_project(request: Request, project: ProjectCreate, db: Session = Depends(get_db)):
    user = require_user(request, db)
    new_project = models.Project(
        user_id=user.id,
        name=project.name.strip(),
        description=project.description,
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project


@app.put("/api/projects/{project_id}")
async def update_project(
    request: Request, project_id: str, project: ProjectUpdate, db: Session = Depends(get_db)
):
    user = require_user(request, db)
    db_project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.user_id == user.id,
    ).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    db_project.name = project.name.strip()
    db_project.description = project.description
    db.commit()
    db.refresh(db_project)
    return db_project


@app.delete("/api/projects/{project_id}")
async def delete_project(request: Request, project_id: str, db: Session = Depends(get_db)):
    user = require_user(request, db)
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.user_id == user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for chat in db.query(models.ChatSession).filter(models.ChatSession.project_id == project_id):
        chat.project_id = None
    db.delete(project)
    db.commit()
    return {"status": "success"}


@app.get("/api/projects/{project_id}/chats")
async def get_project_chats(request: Request, project_id: str, db: Session = Depends(get_db)):
    user = require_user(request, db)
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.user_id == user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return db.query(models.ChatSession).filter(models.ChatSession.project_id == project_id).all()


@app.post("/api/websearch")
async def web_search(
    request: Request,
    body: WebSearchRequest,
    db: Session = Depends(get_db),
):
    require_user(request, db)
    try:
        import requests
        from urllib.parse import quote

        search_url = f"https://api.duckduckgo.com/?q={quote(body.query)}&format=json&pretty=1"
        response = requests.get(search_url, timeout=10)
        results = []

        if response.status_code == 200:
            data = response.json()
            if data.get("AbstractText"):
                results.append({
                    "title": data.get("Heading", "Summary"),
                    "url": data.get("AbstractURL", ""),
                    "snippet": data.get("AbstractText", "")[:500],
                })
            if isinstance(data.get("Results"), list):
                for result in data["Results"][:3]:
                    results.append({
                        "title": result.get("Text", "Result").split(" - ")[0],
                        "url": result.get("FirstURL", ""),
                        "snippet": result.get("Text", ""),
                    })
            if "RelatedTopics" in data:
                for topic in data["RelatedTopics"][:5]:
                    if isinstance(topic, dict) and "FirstURL" in topic:
                        results.append({
                            "title": topic.get("Text", "").split(" - ")[0] or "Related Topic",
                            "url": topic.get("FirstURL", ""),
                            "snippet": topic.get("Text", ""),
                        })
                    elif isinstance(topic, dict) and "Topics" in topic:
                        for subtopic in topic["Topics"][:2]:
                            results.append({
                                "title": subtopic.get("Text", "").split(" - ")[0] or "Related Topic",
                                "url": subtopic.get("FirstURL", ""),
                                "snippet": subtopic.get("Text", ""),
                            })

        unique_results = []
        seen_urls = set()
        for r in results:
            if r["url"] and r["url"] not in seen_urls:
                unique_results.append(r)
                seen_urls.add(r["url"])
        return {"results": unique_results[:5]}

    except Exception as e:
        print(f"Web search error: {e}")
        return {
            "results": [{
                "title": "Search temporarily unavailable",
                "url": "https://duckduckgo.com",
                "snippet": "Web search is currently experiencing issues. Please try again later.",
            }]
        }


@app.post("/api/upload")
async def upload_file(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    require_user(request, db)

    content = await file.read()
    if len(content) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB.")

    file_type = mimetypes.guess_type(file.filename or "")[0] or "application/octet-stream"
    is_image = file_type.startswith("image/")

    if file_type not in config.ALLOWED_UPLOAD_TYPES and not is_image:
        raise HTTPException(status_code=400, detail=f"File type not allowed: {file_type}")

    if is_image:
        base64_data = base64.b64encode(content).decode("utf-8")
        file_content = f"data:{file_type};base64,{base64_data}"
    else:
        try:
            file_content = content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="Only text-based files are supported for non-images.")

    return FileUploadResponse(
        filename=file.filename or "upload",
        file_type=file_type,
        size=len(content),
        content=file_content,
        is_image=is_image,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
