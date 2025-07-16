"""
進化改善パーサー
進化クルーの結果を解析し、実行可能な改善を抽出
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import structlog

logger = structlog.get_logger()


class ImprovementParser:
    """進化クルーの結果を実行可能な改善に解析"""
    
    def __init__(self):
        self.improvement_patterns = {
            "knowledge": {
                "add": r"(?:add|include|追加).*?knowledge.*?[:\s]+(.+?)(?:\n|$)",
                "update": r"(?:update|modify|更新).*?knowledge.*?[:\s]+(.+?)(?:\n|$)",
                "remove": r"(?:remove|delete|削除).*?knowledge.*?[:\s]+(.+?)(?:\n|$)"
            },
            "agent": {
                "role": r"(?:agent|エージェント).*?(?:role|役割).*?[:\s]+(.+?)(?:\n|$)",
                "goal": r"(?:agent|エージェント).*?(?:goal|目標).*?[:\s]+(.+?)(?:\n|$)",
                "backstory": r"(?:agent|エージェント).*?(?:backstory|背景).*?[:\s]+(.+?)(?:\n|$)",
                "tools": r"(?:agent|エージェント).*?(?:tools?|ツール).*?[:\s]+(.+?)(?:\n|$)"
            },
            "task": {
                "description": r"(?:task|タスク).*?(?:description|説明).*?[:\s]+(.+?)(?:\n|$)",
                "expected_output": r"(?:task|タスク).*?(?:output|出力).*?[:\s]+(.+?)(?:\n|$)"
            },
            "config": {
                "memory": r"(?:memory|メモリ).*?(?:config|設定).*?[:\s]+(.+?)(?:\n|$)",
                "process": r"(?:process|プロセス).*?(?:type|タイプ).*?[:\s]+(.+?)(?:\n|$)",
                "tools": r"(?:tool|ツール).*?(?:add|追加).*?[:\s]+(.+?)(?:\n|$)"
            }
        }
    
    def parse_improvement(self, improvement: Dict[str, Any]) -> List[Tuple[str, str, Dict[str, Any]]]:
        """
        単一の改善辞書を(file_path, action, changes)形式に解析
        
        Args:
            improvement: file, action, content/field/valueキーを持つ辞書
            
        Returns:
            (file_path, action, changes)タプルのリスト
        """
        file_path = improvement.get("file", "")
        action = improvement.get("action", "")
        
        changes = {}
        if "content" in improvement:
            changes["content"] = improvement["content"]
        if "field" in improvement:
            changes["field"] = improvement["field"]
        if "value" in improvement:
            changes["value"] = improvement["value"]
        
        return [(file_path, action, changes)]
    
    def parse_improvements(self, evolution_result: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        進化結果テキストを構造化された改善に解析
        
        Returns:
            カテゴリーを持つ辞書: knowledge, agents, tasks, config
        """
        improvements = {
            "knowledge": [],
            "agents": [],
            "tasks": [],
            "config": []
        }
        
        try:
            # テキストを正規化
            text = evolution_result.lower()
            
            # 知識改善を抽出
            improvements["knowledge"] = self._extract_knowledge_improvements(text, evolution_result)
            
            # エージェント改善を抽出
            improvements["agents"] = self._extract_agent_improvements(text, evolution_result)
            
            # タスク改善を抽出
            improvements["tasks"] = self._extract_task_improvements(text, evolution_result)
            
            # 設定改善を抽出
            improvements["config"] = self._extract_config_improvements(text, evolution_result)
            
            # 構造化されたセクションの抽出も試みる
            structured = self._extract_structured_sections(evolution_result)
            if structured:
                improvements = self._merge_improvements(improvements, structured)
            
            logger.info(
                "Parsed improvements",
                knowledge=len(improvements["knowledge"]),
                agents=len(improvements["agents"]),
                tasks=len(improvements["tasks"]),
                config=len(improvements["config"])
            )
            
        except Exception as e:
            logger.error("Failed to parse improvements", error=str(e))
        
        return improvements
    
    def _extract_knowledge_improvements(self, text: str, original: str) -> List[Dict[str, Any]]:
        """知識関連の改善を抽出"""
        improvements = []
        
        # 知識ファイルの更新を探す
        if "knowledge" in text or "知識" in text:
            # 特定の知識追加を抽出
            add_matches = re.findall(
                r"(?:add|include|追加).*?knowledge.*?[:\s]+([^\n]+)",
                original,
                re.IGNORECASE
            )
            for match in add_matches:
                improvements.append({
                    "action": "add",
                    "target": "general",
                    "content": match.strip()
                })
            
            # 知識更新を抽出
            update_matches = re.findall(
                r"(?:update|modify|更新).*?knowledge.*?[:\s]+([^\n]+)",
                original,
                re.IGNORECASE
            )
            for match in update_matches:
                improvements.append({
                    "action": "update",
                    "target": "general",
                    "content": match.strip()
                })
        
        return improvements
    
    def _extract_agent_improvements(self, text: str, original: str) -> List[Dict[str, Any]]:
        """エージェント関連の改善を抽出"""
        improvements = []
        
        # エージェント固有の改善を探す
        agent_sections = re.findall(
            r"(?:agent|エージェント)[:\s]+([^\n]+).*?(?:improvement|改善)[:\s]+([^\n]+)",
            original,
            re.IGNORECASE | re.DOTALL
        )
        
        for agent_name, improvement in agent_sections:
            improvements.append({
                "agent": agent_name.strip(),
                "improvement": improvement.strip()
            })
        
        # 特定フィールドの更新を探す
        for field in ["role", "goal", "backstory", "tools"]:
            field_matches = re.findall(
                rf"(\w+_agent).*?{field}.*?[:\s]+([^\n]+)",
                original,
                re.IGNORECASE
            )
            for agent, value in field_matches:
                improvements.append({
                    "agent": agent,
                    "field": field,
                    "value": value.strip()
                })
        
        return improvements
    
    def _extract_task_improvements(self, text: str, original: str) -> List[Dict[str, Any]]:
        """タスク関連の改善を抽出"""
        improvements = []
        
        # タスク改善を探す
        task_sections = re.findall(
            r"(?:task|タスク)[:\s]+([^\n]+).*?(?:improvement|改善)[:\s]+([^\n]+)",
            original,
            re.IGNORECASE | re.DOTALL
        )
        
        for task_name, improvement in task_sections:
            improvements.append({
                "task": task_name.strip(),
                "improvement": improvement.strip()
            })
        
        return improvements
    
    def _extract_config_improvements(self, text: str, original: str) -> List[Dict[str, Any]]:
        """設定改善を抽出"""
        improvements = []
        
        # 設定変更を探す
        config_patterns = [
            (r"memory.*?(?:enable|disable|設定)", "memory"),
            (r"cache.*?(?:enable|disable|設定)", "cache"),
            (r"process.*?(?:sequential|hierarchical)", "process"),
            (r"tool.*?(?:add|remove|追加|削除)", "tools")
        ]
        
        for pattern, config_type in config_patterns:
            matches = re.findall(pattern, original, re.IGNORECASE)
            for match in matches:
                improvements.append({
                    "type": config_type,
                    "change": match
                })
        
        return improvements
    
    def _extract_structured_sections(self, text: str) -> Optional[Dict[str, List[Any]]]:
        """構造化されたセクションから改善を抽出"""
        structured = {}
        
        # 番号付きまたは箇条書きリストを探す
        sections = re.split(r'\n(?=\d+\.|[-*]|\w+:)', text)
        
        current_category = None
        for section in sections:
            # カテゴリーヘッダーを検出
            if re.match(r'knowledge|知識', section, re.IGNORECASE):
                current_category = "knowledge"
                structured[current_category] = []
            elif re.match(r'agent|エージェント', section, re.IGNORECASE):
                current_category = "agents"
                structured[current_category] = []
            elif re.match(r'task|タスク', section, re.IGNORECASE):
                current_category = "tasks"
                structured[current_category] = []
            elif re.match(r'config|設定', section, re.IGNORECASE):
                current_category = "config"
                structured[current_category] = []
            
            # 現在のセクションからアイテムを抽出
            if current_category and current_category in structured:
                items = re.findall(r'[*-]\s*(.+)', section)
                structured[current_category].extend(items)
        
        return structured if any(structured.values()) else None
    
    def _merge_improvements(
        self,
        base: Dict[str, List[Any]],
        additional: Dict[str, List[Any]]
    ) -> Dict[str, List[Any]]:
        """2つの改善辞書をマージ"""
        merged = base.copy()
        
        for category, items in additional.items():
            if category in merged:
                # 重複を避ける
                existing = set(str(item) for item in merged[category])
                for item in items:
                    if str(item) not in existing:
                        merged[category].append(item)
        
        return merged
    
    def extract_actionable_changes(
        self,
        improvements: Dict[str, List[Any]]
    ) -> List[Tuple[str, str, Dict[str, Any]]]:
        """
        改善を実行可能な変更に変換
        
        Returns:
            (file_path, action, changes)タプルのリスト
        """
        actions = []
        
        # 知識ファイルの変更
        for improvement in improvements.get("knowledge", []):
            if isinstance(improvement, dict):
                action = improvement.get("action", "update")
                content = improvement.get("content", "")
                
                actions.append((
                    "knowledge/general.md",
                    action,
                    {"content": content}
                ))
        
        # エージェント設定の変更
        for improvement in improvements.get("agents", []):
            if isinstance(improvement, dict):
                agent = improvement.get("agent", "")
                field = improvement.get("field")
                value = improvement.get("value")
                
                if agent and field:
                    actions.append((
                        f"config/agents/{agent}.yaml",
                        "update_field",
                        {"field": field, "value": value}
                    ))
        
        # タスク設定の変更
        for improvement in improvements.get("tasks", []):
            if isinstance(improvement, dict):
                task = improvement.get("task", "")
                change = improvement.get("improvement", "")
                
                if task:
                    actions.append((
                        f"config/tasks/{task}.yaml",
                        "update",
                        {"change": change}
                    ))
        
        # 設定変更
        for improvement in improvements.get("config", []):
            if isinstance(improvement, dict):
                config_type = improvement.get("type", "")
                change = improvement.get("change", "")
                
                if config_type == "memory":
                    actions.append((
                        "config/crews/main_crew.yaml",
                        "update_field",
                        {"field": "memory", "value": "enable" in change}
                    ))
                elif config_type == "cache":
                    actions.append((
                        "config/crews/main_crew.yaml",
                        "update_field",
                        {"field": "cache", "value": "enable" in change}
                    ))
        
        return actions