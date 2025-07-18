"""
OKAMIシステム用ガードレールマネージャ
タスク検証・幻覚検出・品質保証を担当
"""

from typing import Callable, Tuple, Any, Dict, List, Optional, Union
import json
import re
import structlog
from crewai import LLM
from crewai.tasks.hallucination_guardrail import HallucinationGuardrail

logger = structlog.get_logger()


class GuardrailManager:
    """OKAMIタスク用ガードレール管理クラス"""

    def __init__(self, llm_model: str = "gpt-4o-mini"):
        """
        ガードレールマネージャの初期化

        Args:
            llm_model: ガードレール検証用LLMモデル
        """
        self.llm = LLM(model=llm_model)
        self.guardrails: Dict[str, Callable] = {}
        self._init_default_guardrails()

        logger.info("Guardrail Manager initialized", llm_model=llm_model)

    def _init_default_guardrails(self) -> None:
        """デフォルトのガードレールを初期化"""
        # JSON validation
        self.guardrails["json"] = self.validate_json_output

        # Email validation
        self.guardrails["email"] = self.validate_email_format

        # Sensitive info filter
        self.guardrails["sensitive"] = self.filter_sensitive_info

        # Word count validation
        self.guardrails["word_count"] = self.validate_word_count

        # Quality check
        self.guardrails["quality"] = self.validate_quality

    def create_hallucination_guardrail(
        self,
        context: Optional[str] = None,
        threshold: float = 7.0,
        tool_response: Optional[str] = None,
    ) -> HallucinationGuardrail:
        """
        幻覚検出用ガードレールを作成

        Args:
            context: 参照コンテキスト
            threshold: 忠実度スコア閾値（0-10）
            tool_response: ツール応答の追加文脈

        Returns:
            HallucinationGuardrailインスタンス
        """
        return HallucinationGuardrail(
            context=context,
            llm=self.llm,
            threshold=threshold,
            tool_response=tool_response,
        )

    def validate_json_output(self, result: str) -> Tuple[bool, Union[Dict, str]]:
        """出力が有効なJSONか検証"""
        try:
            json_data = json.loads(result)
            return (True, json_data)
        except json.JSONDecodeError as e:
            return (False, f"Invalid JSON: {str(e)}")

    def validate_email_format(self, result: str) -> Tuple[bool, Union[str, str]]:
        """メールアドレス形式を検証"""
        email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if re.match(email_pattern, result.strip()):
            return (True, result.strip())
        return (False, "Output must be a valid email address")

    def filter_sensitive_info(self, result: str) -> Tuple[bool, Union[str, str]]:
        """機密情報をフィルタリング"""
        sensitive_patterns = ["SSN:", "password:", "secret:", "api_key:", "token:"]
        for pattern in sensitive_patterns:
            if pattern.lower() in result.lower():
                return (False, f"Output contains sensitive information ({pattern})")
        return (True, result)

    def validate_word_count(
        self, max_words: int = 200
    ) -> Callable[[str], Tuple[bool, Any]]:
        """語数上限バリデータを作成"""

        def validator(result: str) -> Tuple[bool, Any]:
            word_count = len(result.split())
            if word_count > max_words:
                return (False, f"Output exceeds {max_words} words (found {word_count})")
            return (True, result.strip())

        return validator

    def validate_quality(self, result: str) -> Tuple[bool, Any]:
        """基本的な品質検証"""
        # Check minimum length
        if len(result.strip()) < 10:
            return (False, "Output is too short")

        # Check for placeholder text
        placeholders = ["TODO", "FIXME", "[INSERT", "XXX"]
        for placeholder in placeholders:
            if placeholder in result:
                return (False, f"Output contains placeholder text: {placeholder}")

        return (True, result)

    def chain_validators(
        self, *validators: Callable
    ) -> Callable[[str], Tuple[bool, Any]]:
        """
        複数バリデータを連結

        Args:
            validators: 連結するバリデータ関数

        Returns:
            連結バリデータ関数
        """

        def combined_validator(result: str) -> Tuple[bool, Any]:
            for validator in validators:
                success, data = validator(result)
                if not success:
                    return (False, data)
                result = data if isinstance(data, str) else result
            return (True, result)

        return combined_validator

    def get_guardrail(self, guardrail_type: str) -> Optional[Callable]:
        """
        ガードレール種別で取得

        Args:
            guardrail_type: ガードレール種別

        Returns:
            ガードレール関数またはNone
        """
        return self.guardrails.get(guardrail_type)

    def add_custom_guardrail(
        self, name: str, validator: Callable[[str], Tuple[bool, Any]]
    ) -> None:
        """
        カスタムガードレールを追加

        Args:
            name: ガードレール名
            validator: バリデータ関数
        """
        self.guardrails[name] = validator
        logger.info("Custom guardrail added", name=name)

    def create_llm_guardrail(
        self, description: str, custom_llm: Optional[LLM] = None
    ) -> Callable:
        """
        LLMベースのガードレールを作成

        Args:
            description: バリデーション要件の自然言語説明
            custom_llm: カスタムLLM

        Returns:
            ガードレール関数
        """
        llm = custom_llm or self.llm

        def llm_validator(result: str) -> Tuple[bool, Any]:
            try:
                # Use LLM to validate
                prompt = f"""
                Validate the following output based on this requirement: {description}
                
                Output: {result}
                
                Return JSON with:
                - "valid": boolean
                - "reason": string (if invalid)
                - "fixed_output": string (if you can fix it)
                """

                response = llm.call(messages=[{"role": "user", "content": prompt}])
                validation = json.loads(response.choices[0].message.content)

                if validation["valid"]:
                    return (True, result)
                else:
                    if "fixed_output" in validation:
                        return (True, validation["fixed_output"])
                    return (False, validation.get("reason", "Validation failed"))

            except Exception as e:
                logger.error(f"LLM validation failed: {e}")
                return (False, f"LLM validation error: {str(e)}")

        return llm_validator