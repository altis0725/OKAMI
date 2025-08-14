"""Evolution Crew出力用のPydanticモデル"""

from typing import List, Union, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class ChangeBase(BaseModel):
    """変更の基本モデル"""
    type: str = Field(..., description="変更タイプ")
    reason: str = Field(..., description="変更理由")


class KnowledgeCategory(str, Enum):
    """知識カテゴリ"""
    AGENT = "agents"
    CREW = "crew"
    SYSTEM = "system"
    DOMAIN = "domain"
    GENERAL = "general"


class AddKnowledge(ChangeBase):
    """知識追加"""
    type: str = Field(default="add_knowledge")
    category: KnowledgeCategory = Field(
        KnowledgeCategory.GENERAL, 
        description="知識カテゴリ"
    )
    file: str = Field(..., description="ファイルパス")
    title: str = Field(..., description="知識タイトル")
    content: str = Field(..., description="追加内容")
    tags: List[str] = Field(default_factory=list, description="タグリスト")


class UpdateKnowledge(ChangeBase):
    """既存知識の更新"""
    type: str = Field(default="update_knowledge")
    file: str = Field(..., description="更新対象ファイルパス")
    section: Optional[str] = Field(None, description="更新対象セクション")
    content: str = Field(..., description="更新内容")
    operation: str = Field("append", description="更新操作: append, replace, insert")


class EvolutionChanges(BaseModel):
    """Evolution Crewの改善案出力（知識管理特化）"""
    changes: List[Union[AddKnowledge, UpdateKnowledge]] = Field(
        ..., 
        description="知識改善案のリスト"
    )