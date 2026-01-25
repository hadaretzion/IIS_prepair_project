from pydantic import BaseModel

class InterviewSkipToCodeRequest(BaseModel):
    session_id: str
