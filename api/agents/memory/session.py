"""Conversation memory for one analysis. Nothing is kept between analyses."""

import uuid

from google.adk.sessions import InMemorySessionService

APP_NAME = "harvestwatch"
USER_ID = "analyst"


async def new_session():
    service = InMemorySessionService()
    session = await service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=uuid.uuid4().hex)
    return service, session
