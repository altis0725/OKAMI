"""
Claude Code Quality Monitor for OKAMI system
Monitors CrewAI response time and quality, provides improvement instructions
"""

import os
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
import httpx
import structlog
from enum import Enum

logger = structlog.get_logger()


class QualityLevel(Enum):
    """Quality assessment levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    UNACCEPTABLE = "unacceptable"


class ResponseQuality:
    """Response quality assessment"""
    
    def __init__(
        self,
        task_id: str,
        response_time: float,
        content: str,
        task_description: str,
        expected_output: str
    ):
        self.task_id = task_id
        self.response_time = response_time
        self.content = content
        self.task_description = task_description
        self.expected_output = expected_output
        self.timestamp = datetime.utcnow()
        
        # Assessment results
        self.time_quality: QualityLevel = QualityLevel.GOOD
        self.content_quality: QualityLevel = QualityLevel.GOOD
        self.overall_quality: QualityLevel = QualityLevel.GOOD
        self.issues: List[str] = []
        self.improvements: List[str] = []


class ClaudeQualityMonitor:
    """Quality monitor for CrewAI responses"""

    def __init__(
        self,
        okami_api_url: str = "http://localhost:8000",
        check_interval: int = 30,
        response_time_thresholds: Optional[Dict[str, float]] = None,
    ):
        """
        Initialize Quality Monitor

        Args:
            okami_api_url: OKAMI API URL
            check_interval: Check interval in seconds
            response_time_thresholds: Response time thresholds by task type
        """
        self.okami_api_url = okami_api_url
        self.check_interval = check_interval
        
        # Default response time thresholds (in seconds)
        self.response_time_thresholds = response_time_thresholds or {
            "simple": 5.0,      # Simple queries
            "research": 30.0,   # Research tasks
            "analysis": 20.0,   # Analysis tasks
            "writing": 15.0,    # Writing tasks
            "default": 10.0     # Default threshold
        }
        
        self.client = httpx.AsyncClient(timeout=60.0)
        self.monitoring_active = False
        
        # Quality history
        self.quality_history: List[ResponseQuality] = []
        self.improvement_queue: List[Dict[str, Any]] = []
        
        logger.info(
            "Claude Quality Monitor initialized",
            okami_api_url=okami_api_url,
            check_interval=check_interval
        )

    async def start_monitoring(self) -> None:
        """Start the monitoring loop"""
        self.monitoring_active = True
        logger.info("Quality monitoring started")
        
        while self.monitoring_active:
            try:
                await self._monitor_active_tasks()
                await self._process_improvement_queue()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Monitor cycle error: {e}")
                await asyncio.sleep(5)

    async def stop_monitoring(self) -> None:
        """Stop the monitoring loop"""
        self.monitoring_active = False
        await self.client.aclose()
        logger.info("Quality monitoring stopped")

    async def _monitor_active_tasks(self) -> None:
        """Monitor active tasks and recently completed ones"""
        try:
            # Get recent task completions
            response = await self.client.get(f"{self.okami_api_url}/tasks/recent")
            if response.status_code == 200:
                tasks = response.json()
                
                for task in tasks:
                    if task.get("status") == "completed":
                        await self._assess_task_quality(task)
                        
        except Exception as e:
            logger.error(f"Failed to monitor tasks: {e}")

    async def _assess_task_quality(self, task_data: Dict[str, Any]) -> None:
        """
        Assess the quality of a completed task

        Args:
            task_data: Task execution data
        """
        quality = ResponseQuality(
            task_id=task_data["task_id"],
            response_time=task_data.get("execution_time", 0),
            content=task_data.get("result", ""),
            task_description=task_data.get("task_description", ""),
            expected_output=task_data.get("expected_output", "")
        )
        
        # Assess response time
        quality.time_quality = self._assess_response_time(
            quality.response_time,
            self._determine_task_type(quality.task_description)
        )
        
        # Assess content quality
        quality.content_quality = await self._assess_content_quality(
            quality.content,
            quality.task_description,
            quality.expected_output
        )
        
        # Determine overall quality
        quality.overall_quality = self._determine_overall_quality(
            quality.time_quality,
            quality.content_quality
        )
        
        # Generate improvements if needed
        if quality.overall_quality in [QualityLevel.POOR, QualityLevel.UNACCEPTABLE]:
            improvements = self._generate_improvements(quality)
            if improvements:
                self.improvement_queue.extend(improvements)
        
        # Store in history
        self.quality_history.append(quality)
        
        # Keep only last 1000 assessments
        if len(self.quality_history) > 1000:
            self.quality_history = self.quality_history[-1000:]
        
        logger.info(
            "Task quality assessed",
            task_id=quality.task_id,
            time_quality=quality.time_quality.value,
            content_quality=quality.content_quality.value,
            overall_quality=quality.overall_quality.value,
            issues=len(quality.issues)
        )

    def _assess_response_time(self, response_time: float, task_type: str) -> QualityLevel:
        """
        Assess response time quality

        Args:
            response_time: Response time in seconds
            task_type: Type of task

        Returns:
            Quality level
        """
        threshold = self.response_time_thresholds.get(
            task_type,
            self.response_time_thresholds["default"]
        )
        
        if response_time <= threshold * 0.5:
            return QualityLevel.EXCELLENT
        elif response_time <= threshold:
            return QualityLevel.GOOD
        elif response_time <= threshold * 1.5:
            return QualityLevel.ACCEPTABLE
        elif response_time <= threshold * 2:
            return QualityLevel.POOR
        else:
            return QualityLevel.UNACCEPTABLE

    async def _assess_content_quality(
        self,
        content: str,
        task_description: str,
        expected_output: str
    ) -> QualityLevel:
        """
        Assess content quality using various criteria

        Args:
            content: Response content
            task_description: Original task description
            expected_output: Expected output format

        Returns:
            Quality level
        """
        issues = []
        score = 100  # Start with perfect score
        
        # Check content exists and has reasonable length
        if not content or len(content.strip()) < 10:
            issues.append("Content too short or empty")
            score -= 50
        
        # Check for placeholder text
        placeholders = ["TODO", "FIXME", "[INSERT", "Lorem ipsum"]
        for placeholder in placeholders:
            if placeholder in content:
                issues.append(f"Contains placeholder text: {placeholder}")
                score -= 20
        
        # Check if expected format requirements are met
        if "json" in expected_output.lower() and not self._is_valid_json(content):
            issues.append("Expected JSON format but content is not valid JSON")
            score -= 30
        
        if "bullet points" in expected_output.lower() and not any(marker in content for marker in ["•", "-", "*", "1."]):
            issues.append("Expected bullet points but none found")
            score -= 20
        
        # Check for completeness based on expected output
        expected_sections = self._extract_expected_sections(expected_output)
        missing_sections = []
        for section in expected_sections:
            if section.lower() not in content.lower():
                missing_sections.append(section)
        
        if missing_sections:
            issues.append(f"Missing expected sections: {', '.join(missing_sections)}")
            score -= 10 * len(missing_sections)
        
        # Check for errors or warnings in content
        error_indicators = ["error:", "failed:", "exception:", "traceback:"]
        for indicator in error_indicators:
            if indicator.lower() in content.lower():
                issues.append(f"Content contains error indicator: {indicator}")
                score -= 25
        
        # Determine quality level based on score
        if score >= 90:
            return QualityLevel.EXCELLENT
        elif score >= 75:
            return QualityLevel.GOOD
        elif score >= 60:
            return QualityLevel.ACCEPTABLE
        elif score >= 40:
            return QualityLevel.POOR
        else:
            return QualityLevel.UNACCEPTABLE

    def _determine_task_type(self, task_description: str) -> str:
        """Determine task type from description"""
        task_lower = task_description.lower()
        
        if any(word in task_lower for word in ["research", "investigate", "find", "search"]):
            return "research"
        elif any(word in task_lower for word in ["analyze", "analysis", "evaluate", "assess"]):
            return "analysis"
        elif any(word in task_lower for word in ["write", "create", "draft", "compose"]):
            return "writing"
        elif any(word in task_lower for word in ["simple", "quick", "brief", "list"]):
            return "simple"
        else:
            return "default"

    def _is_valid_json(self, content: str) -> bool:
        """Check if content is valid JSON"""
        try:
            json.loads(content)
            return True
        except:
            return False

    def _extract_expected_sections(self, expected_output: str) -> List[str]:
        """Extract expected sections from output description"""
        sections = []
        
        # Look for numbered items (1., 2., etc.)
        import re
        numbered_items = re.findall(r'\d+\.\s*([^.]+)', expected_output)
        sections.extend(numbered_items)
        
        # Look for bullet points
        bullet_items = re.findall(r'[-•*]\s*([^-•*\n]+)', expected_output)
        sections.extend(bullet_items)
        
        # Look for key terms
        key_terms = ["summary", "findings", "recommendations", "conclusion", "analysis"]
        for term in key_terms:
            if term in expected_output.lower():
                sections.append(term)
        
        return sections

    def _determine_overall_quality(
        self,
        time_quality: QualityLevel,
        content_quality: QualityLevel
    ) -> QualityLevel:
        """Determine overall quality from components"""
        # Map quality levels to scores
        quality_scores = {
            QualityLevel.EXCELLENT: 5,
            QualityLevel.GOOD: 4,
            QualityLevel.ACCEPTABLE: 3,
            QualityLevel.POOR: 2,
            QualityLevel.UNACCEPTABLE: 1
        }
        
        # Weight content quality more heavily (70/30)
        weighted_score = (
            quality_scores[content_quality] * 0.7 +
            quality_scores[time_quality] * 0.3
        )
        
        # Map back to quality level
        if weighted_score >= 4.5:
            return QualityLevel.EXCELLENT
        elif weighted_score >= 3.5:
            return QualityLevel.GOOD
        elif weighted_score >= 2.5:
            return QualityLevel.ACCEPTABLE
        elif weighted_score >= 1.5:
            return QualityLevel.POOR
        else:
            return QualityLevel.UNACCEPTABLE

    def _generate_improvements(self, quality: ResponseQuality) -> List[Dict[str, Any]]:
        """
        Generate improvement instructions

        Args:
            quality: Quality assessment

        Returns:
            List of improvement instructions
        """
        improvements = []
        
        # Response time improvements
        if quality.time_quality in [QualityLevel.POOR, QualityLevel.UNACCEPTABLE]:
            improvements.append({
                "type": "performance",
                "target": "crew_optimization",
                "instruction": "Optimize task execution for faster response",
                "suggestions": [
                    "Enable caching for repeated queries",
                    "Reduce unnecessary tool calls",
                    "Parallelize independent subtasks",
                    "Simplify agent reasoning chains"
                ]
            })
        
        # Content quality improvements
        if quality.content_quality in [QualityLevel.POOR, QualityLevel.UNACCEPTABLE]:
            content_improvements = {
                "type": "content_quality",
                "target": "agent_instructions",
                "instruction": "Improve response content quality",
                "issues": quality.issues,
                "suggestions": []
            }
            
            # Specific suggestions based on issues
            if "too short" in str(quality.issues):
                content_improvements["suggestions"].append(
                    "Increase response detail and comprehensiveness"
                )
            
            if "placeholder" in str(quality.issues):
                content_improvements["suggestions"].append(
                    "Ensure all placeholder text is replaced with actual content"
                )
            
            if "JSON format" in str(quality.issues):
                content_improvements["suggestions"].append(
                    "Validate JSON output format before returning"
                )
            
            if "Missing expected sections" in str(quality.issues):
                content_improvements["suggestions"].append(
                    "Ensure all required sections are included in the response"
                )
            
            improvements.append(content_improvements)
        
        # Task-specific improvements
        task_type = self._determine_task_type(quality.task_description)
        if task_type == "research" and quality.overall_quality != QualityLevel.EXCELLENT:
            improvements.append({
                "type": "task_specific",
                "target": "research_agent",
                "instruction": "Enhance research quality",
                "suggestions": [
                    "Include more diverse sources",
                    "Provide deeper analysis of findings",
                    "Add source citations and credibility assessment"
                ]
            })
        
        return improvements

    async def _process_improvement_queue(self) -> None:
        """Process queued improvements"""
        if not self.improvement_queue:
            return
        
        # Group improvements by target
        grouped_improvements = {}
        for improvement in self.improvement_queue:
            target = improvement["target"]
            if target not in grouped_improvements:
                grouped_improvements[target] = []
            grouped_improvements[target].append(improvement)
        
        # Send improvement instructions
        for target, improvements in grouped_improvements.items():
            await self._send_improvement_instruction(target, improvements)
        
        # Clear the queue
        self.improvement_queue.clear()

    async def _send_improvement_instruction(
        self,
        target: str,
        improvements: List[Dict[str, Any]]
    ) -> None:
        """
        Send improvement instruction to OKAMI system

        Args:
            target: Target component
            improvements: List of improvements
        """
        try:
            instruction = {
                "target": target,
                "timestamp": datetime.utcnow().isoformat(),
                "improvements": improvements,
                "priority": "high" if any(
                    i["type"] == "content_quality" for i in improvements
                ) else "medium"
            }
            
            # Send to OKAMI system
            response = await self.client.post(
                f"{self.okami_api_url}/improvements",
                json=instruction
            )
            
            if response.status_code == 200:
                logger.info(
                    "Improvement instruction sent",
                    target=target,
                    improvement_count=len(improvements)
                )
            else:
                logger.error(
                    "Failed to send improvement instruction",
                    target=target,
                    status_code=response.status_code
                )
                
        except Exception as e:
            logger.error(f"Error sending improvement instruction: {e}")

    async def get_quality_report(self) -> Dict[str, Any]:
        """
        Get comprehensive quality report

        Returns:
            Quality report
        """
        if not self.quality_history:
            return {
                "status": "no_data",
                "message": "No quality assessments available yet"
            }
        
        # Calculate statistics
        recent_window = datetime.utcnow() - timedelta(hours=1)
        recent_assessments = [
            q for q in self.quality_history
            if q.timestamp > recent_window
        ]
        
        # Quality distribution
        quality_distribution = {
            level.value: 0 for level in QualityLevel
        }
        
        time_quality_dist = quality_distribution.copy()
        content_quality_dist = quality_distribution.copy()
        
        total_response_time = 0
        
        for assessment in recent_assessments:
            quality_distribution[assessment.overall_quality.value] += 1
            time_quality_dist[assessment.time_quality.value] += 1
            content_quality_dist[assessment.content_quality.value] += 1
            total_response_time += assessment.response_time
        
        avg_response_time = (
            total_response_time / len(recent_assessments)
            if recent_assessments else 0
        )
        
        # Common issues
        all_issues = []
        for assessment in recent_assessments:
            all_issues.extend(assessment.issues)
        
        issue_frequency = {}
        for issue in all_issues:
            issue_frequency[issue] = issue_frequency.get(issue, 0) + 1
        
        # Sort issues by frequency
        common_issues = sorted(
            issue_frequency.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "assessment_count": len(recent_assessments),
            "time_window": "1 hour",
            "average_response_time": avg_response_time,
            "quality_distribution": quality_distribution,
            "time_quality_distribution": time_quality_dist,
            "content_quality_distribution": content_quality_dist,
            "common_issues": common_issues,
            "pending_improvements": len(self.improvement_queue),
            "recommendations": self._generate_system_recommendations(
                quality_distribution,
                avg_response_time,
                common_issues
            )
        }

    def _generate_system_recommendations(
        self,
        quality_dist: Dict[str, int],
        avg_response_time: float,
        common_issues: List[Tuple[str, int]]
    ) -> List[str]:
        """Generate system-wide recommendations"""
        recommendations = []
        
        total = sum(quality_dist.values())
        if total == 0:
            return recommendations
        
        # Check overall quality
        poor_quality_ratio = (
            quality_dist.get(QualityLevel.POOR.value, 0) +
            quality_dist.get(QualityLevel.UNACCEPTABLE.value, 0)
        ) / total
        
        if poor_quality_ratio > 0.3:
            recommendations.append(
                "High ratio of poor quality responses. Consider reviewing agent prompts and task definitions."
            )
        
        # Check response time
        if avg_response_time > 15:
            recommendations.append(
                "Average response time is high. Consider optimizing crew workflows and enabling caching."
            )
        
        # Check common issues
        if common_issues and common_issues[0][1] > 5:
            recommendations.append(
                f"Frequent issue detected: '{common_issues[0][0]}'. Address this systematically."
            )
        
        return recommendations


async def main():
    """Main function for running the quality monitor"""
    monitor = ClaudeQualityMonitor(
        okami_api_url=os.getenv("OKAMI_API_URL", "http://localhost:8000"),
        check_interval=int(os.getenv("QUALITY_CHECK_INTERVAL", "30"))
    )
    
    try:
        await monitor.start_monitoring()
    except KeyboardInterrupt:
        logger.info("Quality monitoring interrupted by user")
        await monitor.stop_monitoring()


if __name__ == "__main__":
    asyncio.run(main())