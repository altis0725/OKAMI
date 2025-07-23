"""Evolution Crew出力用のPydanticモデル"""

from typing import List, Union, Any
from pydantic import BaseModel, Field


class ChangeBase(BaseModel):
    """変更の基本モデル"""
    type: str = Field(..., description="変更タイプ")
    reason: str = Field(..., description="変更理由")


class UpdateAgentParameter(ChangeBase):
    """エージェントパラメータ更新"""
    type: str = Field(default="update_agent_parameter")
    agent: str = Field(..., description="対象エージェント名")
    parameter: str = Field(..., description="パラメータ名")
    value: Any = Field(..., description="新しい値")


class AddKnowledge(ChangeBase):
    """知識追加"""
    type: str = Field(default="add_knowledge")
    file: str = Field(..., description="ファイルパス")
    content: str = Field(..., description="追加内容")


class CreateAgent(ChangeBase):
    """新規エージェント作成"""
    type: str = Field(default="create_agent")
    file: str = Field(..., description="ファイルパス")
    config: dict = Field(..., description="エージェント設定")


class EvolutionChanges(BaseModel):
    """Evolution Crewの改善案出力"""
    changes: List[Union[UpdateAgentParameter, AddKnowledge, CreateAgent]] = Field(
        ..., 
        description="改善案のリスト"
    )