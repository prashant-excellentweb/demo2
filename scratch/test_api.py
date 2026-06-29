
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi import Request
from main import chat_api, ChatRequest
from database import SessionLocal
import models
import uuid

async def test_chat():
    db = SessionLocal()
    # Mock user
    user = db.query(models.User).first()
    if not user:
        user = models.User(id=str(uuid.uuid4()), username="testuser", hashed_password="hashed")
        db.add(user)
        db.commit()
    
    chat_id = str(uuid.uuid4())
    req = ChatRequest(chat_id=chat_id, messages=[{"role": "user", "content": "hello"}], title="Test Chat")
    
    # Mock request object for get_current_user_obj
    # Since we can't easily mock Request with cookies for get_current_user_obj, 
    # we'll manually patch get_current_user_obj or just call the logic.
    
    print("Starting chat_api call...")
    try:
        # We need a mock request that would return our user
        class MockRequest:
            def __init__(self):
                self.cookies = {}
        
        # Patching get_current_user_obj in main
        import main
        main.get_current_user_obj = lambda r, d: user
        
        result = await chat_api(MockRequest(), req, db)
        print("Result:", result)
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_chat())
