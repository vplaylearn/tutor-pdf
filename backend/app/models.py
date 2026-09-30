from typing import Optional
from pydantic import BaseModel
class AskRequest(BaseModel): document_id:str; question:str
class AnswerBlock(BaseModel): heading:Optional[str]=None; text:str
class Source(BaseModel):
    document_id:str; question_number:Optional[int]=None; question:str; text:str; answer:str
    answer_blocks:list[AnswerBlock]=[]; page:Optional[int]=None; page_start:Optional[int]=None; page_end:Optional[int]=None
    score:float; match_type:str
class AskResponse(BaseModel): answer:str; sources:list[Source]
class DocumentResponse(BaseModel):
    document_id:str; filename:str; title:str; pages:int; records:int; extraction_mode:str; status:str
