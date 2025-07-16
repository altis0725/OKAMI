"""
Guardrail Manager for OKAMI system
Handles task validation, hallucination detection, and quality assurance
"""

from typing import Callable, Tuple, Any, Dict, List, Optional, Union
import json
import re
import structlog
from crewai import LLM
from crewai.tasks.hallucination_guardrail import HallucinationGuardrail

logger = structlog.get_logger()


class GuardrailManager:
    """Manages guardrails for OKAMI tasks"""

    def __init__(self, llm_model: str = "gpt-4o-mini"):
        """
        Initialize Guardrail Manager

        Args:
            llm_model: LLM model for guardrail validation
        """
        self.llm = LLM(model=llm_model)
        self.guardrails: Dict[str, Callable] = {}
        self._init_default_guardrails()

        logger.info("Guardrail Manager initialized", llm_model=llm_model)

    def _init_default_guardrails(self) -> None:
        """Initialize default guardrails"""
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
        Create hallucination detection guardrail

        Args:
            context: Reference context for validation
            threshold: Faithfulness score threshold (0-10)
            tool_response: Optional tool response context

        Returns:
            HallucinationGuardrail instance
        """
        return HallucinationGuardrail(
            context=context,
            llm=self.llm,
            threshold=threshold,
            tool_response=tool_response,
        )

    def validate_json_output(self, result: str) -> Tuple[bool, Union[Dict, str]]:
        """Validate that output is valid JSON"""
        try:
            json_data = json.loads(result)
            return (True, json_data)
        except json.JSONDecodeError as e:
            return (False, f"Invalid JSON: {str(e)}")

    def validate_email_format(self, result: str) -> Tuple[bool, Union[str, str]]:
        """Validate email address format"""
        email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if re.match(email_pattern, result.strip()):
            return (True, result.strip())
        return (False, "Output must be a valid email address")

    def filter_sensitive_info(self, result: str) -> Tuple[bool, Union[str, str]]:
        """Filter sensitive information"""
        sensitive_patterns = ["SSN:", "password:", "secret:", "api_key:", "token:"]
        for pattern in sensitive_patterns:
            if pattern.lower() in result.lower():
                return (False, f"Output contains sensitive information ({pattern})")
        return (True, result)

    def validate_word_count(
        self, max_words: int = 200
    ) -> Callable[[str], Tuple[bool, Any]]:
        """Create word count validator"""

        def validator(result: str) -> Tuple[bool, Any]:
            word_count = len(result.split())
            if word_count > max_words:
                return (False, f"Output exceeds {max_words} words (found {word_count})")
            return (True, result.strip())

        return validator

    def validate_quality(self, result: str) -> Tuple[bool, Any]:
        """Basic quality validation"""
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
        Chain multiple validators

        Args:
            validators: Validator functions to chain

        Returns:
            Combined validator function
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
        Get guardrail by type

        Args:
            guardrail_type: Type of guardrail

        Returns:
            Guardrail function or None
        """
        return self.guardrails.get(guardrail_type)

    def add_custom_guardrail(
        self, name: str, validator: Callable[[str], Tuple[bool, Any]]
    ) -> None:
        """
        Add custom guardrail

        Args:
            name: Guardrail name
            validator: Validator function
        """
        self.guardrails[name] = validator
        logger.info("Custom guardrail added", name=name)

    def create_llm_guardrail(
        self, description: str, custom_llm: Optional[LLM] = None
    ) -> Callable:
        """
        Create LLM-based guardrail

        Args:
            description: Natural language description of validation
            custom_llm: Optional custom LLM

        Returns:
            Guardrail function
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