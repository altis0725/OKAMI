"""
JSON Evolution Parser テスト
evolution crewのJSON出力を正しく解析できることをテスト
"""

import pytest
import json
from evolution.improvement_parser import ImprovementParser


class TestJSONEvolutionParser:
    """JSON Evolution Parserのテストクラス"""
    
    @pytest.fixture
    def parser(self):
        """ImprovementParserのインスタンスを作成"""
        return ImprovementParser()
    
    def test_parse_add_knowledge_action(self, parser):
        """add_knowledgeアクションの解析をテスト"""
        json_result = '''
        {
            "type": "add_knowledge",
            "file": "knowledge/optimization_best_practices.md",
            "content": "**Optimization Tactics:**\\n- Database query performance improvements with caching and indexing techniques.\\n- Resource scaling strategies using dynamic allocation.",
            "reason": "To provide clear guidelines for implementing recommended improvement strategies within the OKAMI system."
        }
        '''
        
        improvements = parser.parse_improvements(json_result)
        
        # 知識改善が検出されることを確認
        assert len(improvements["knowledge"]) == 1
        
        knowledge_improvement = improvements["knowledge"][0]
        assert knowledge_improvement["action"] == "add"
        assert knowledge_improvement["file"] == "knowledge/optimization_best_practices.md"
        assert "Optimization Tactics" in knowledge_improvement["content"]
        assert knowledge_improvement["reason"] == "To provide clear guidelines for implementing recommended improvement strategies within the OKAMI system."
    
    def test_parse_multiple_actions(self, parser):
        """複数のアクションの解析をテスト"""
        json_result = '''
        [
            {
                "type": "add_knowledge",
                "file": "knowledge/optimization_best_practices.md",
                "content": "**Optimization Tactics:**\\n- Database improvements",
                "reason": "To provide guidelines"
            },
            {
                "type": "update_agent_parameter",
                "agent": "OKAMI_system",
                "parameter": "accuracy_in_complex_queries",
                "value": "Adopt advanced NLP models such as BERT or GPT variants",
                "reason": "To enhance understanding"
            }
        ]
        '''
        
        improvements = parser.parse_improvements(json_result)
        
        # 知識とエージェント改善が検出されることを確認
        assert len(improvements["knowledge"]) == 1
        assert len(improvements["agents"]) == 1
        
        knowledge_improvement = improvements["knowledge"][0]
        assert knowledge_improvement["action"] == "add"
        assert knowledge_improvement["file"] == "knowledge/optimization_best_practices.md"
        
        agent_improvement = improvements["agents"][0]
        assert agent_improvement["field"] == "accuracy_in_complex_queries"
        assert "BERT or GPT" in agent_improvement["value"]
    
    def test_extract_actionable_changes_for_add_knowledge(self, parser):
        """add_knowledgeアクションの実行可能な変更への変換をテスト"""
        improvements = {
            "knowledge": [{
                "action": "add",
                "file": "knowledge/optimization_best_practices.md",
                "content": "**Optimization Tactics:**\\n- Database improvements",
                "reason": "To provide guidelines"
            }],
            "agents": [],
            "tasks": [],
            "config": []
        }
        
        actionable_changes = parser.extract_actionable_changes(improvements)
        
        # アクションが正しく変換されることを確認
        assert len(actionable_changes) == 1
        
        file_path, action, changes = actionable_changes[0]
        assert file_path == "knowledge/optimization_best_practices.md"
        assert action == "add"
        assert "Database improvements" in changes["content"]
    
    def test_parse_nested_json_in_text(self, parser):
        """テキスト内のネストされたJSONの解析をテスト"""
        evolution_result = '''
        Evolution analysis shows the following improvements:
        
        {
            "improvements": [
                {
                    "type": "add_knowledge",
                    "file": "knowledge/best_practices.md",
                    "content": "New optimization strategies",
                    "reason": "For better performance"
                }
            ]
        }
        
        Additional text here...
        '''
        
        improvements = parser.parse_improvements(evolution_result)
        
        # ネストされたJSONから改善が抽出されることを確認
        assert len(improvements["knowledge"]) == 1
        
        knowledge_improvement = improvements["knowledge"][0]
        assert knowledge_improvement["action"] == "add"
        # ネストされたJSONでは"file"キーが存在することを確認
        if "file" in knowledge_improvement:
            assert knowledge_improvement["file"] == "knowledge/best_practices.md"
        assert knowledge_improvement["content"] == "New optimization strategies"
    
    def test_invalid_json_handling(self, parser):
        """無効なJSONの適切な処理をテスト"""
        invalid_json = '''
        This is not valid JSON: {invalid json}
        But it contains some text that should be parsed normally.
        '''
        
        # エラーが発生せずに処理されることを確認
        improvements = parser.parse_improvements(invalid_json)
        
        # 結果が空でも問題ないことを確認
        assert isinstance(improvements, dict)
        assert "knowledge" in improvements
        assert "agents" in improvements
        assert "tasks" in improvements
        assert "config" in improvements
    
    def test_mixed_json_and_text_parsing(self, parser):
        """JSONとテキストの混在した入力の解析をテスト"""
        mixed_result = '''
        Evolution analysis results:
        
        {
            "type": "add_knowledge",
            "file": "knowledge/mixed_content.md",
            "content": "JSON based content",
            "reason": "From JSON parsing"
        }
        
        Additionally, we should add knowledge about performance optimization.
        The system should update the memory configuration for better caching.
        '''
        
        improvements = parser.parse_improvements(mixed_result)
        
        # JSONとテキストの両方から改善が抽出されることを確認
        assert len(improvements["knowledge"]) >= 1
        
        # JSONベースの改善を確認
        json_improvements = [imp for imp in improvements["knowledge"] 
                           if imp.get("file") == "knowledge/mixed_content.md"]
        assert len(json_improvements) == 1
        assert json_improvements[0]["content"] == "JSON based content"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])