"""
Knowledge source loader for OKAMI system
"""

import os
from pathlib import Path
from typing import List, Dict, Any
import structlog

logger = structlog.get_logger()


class KnowledgeLoader:
    """Load and manage knowledge sources for CrewAI agents"""
    
    def __init__(self, knowledge_dir: str = None):
        """Initialize knowledge loader
        
        Args:
            knowledge_dir: Directory containing knowledge files
        """
        if knowledge_dir is None:
            knowledge_dir = Path(__file__).parent
        self.knowledge_dir = Path(knowledge_dir)
        self.knowledge_files = self._discover_knowledge_files()
        
    def _discover_knowledge_files(self) -> Dict[str, str]:
        """Discover all knowledge files in the directory
        
        Returns:
            Dictionary mapping knowledge type to filename
        """
        knowledge_files = {}
        
        # Scan for .txt and .md files
        for file_path in self.knowledge_dir.glob("*"):
            if file_path.is_file() and file_path.suffix in ['.txt', '.md']:
                # Use filename without extension as key
                key = file_path.stem.replace('-', '_').replace(' ', '_')
                knowledge_files[key] = file_path.name
                
        logger.info(f"Discovered {len(knowledge_files)} knowledge files", 
                   files=list(knowledge_files.keys()))
        
        return knowledge_files
        
    def load_all_knowledge(self) -> Dict[str, str]:
        """Load all knowledge files
        
        Returns:
            Dictionary mapping knowledge type to content
        """
        knowledge = {}
        
        for key, filename in self.knowledge_files.items():
            filepath = self.knowledge_dir / filename
            if filepath.exists():
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        knowledge[key] = content
                        logger.info(f"Loaded knowledge source: {key}", 
                                  file=filename,
                                  size=len(content))
                except Exception as e:
                    logger.error(f"Failed to load knowledge source: {key}",
                               error=str(e),
                               file=filename)
            else:
                logger.warning(f"Knowledge file not found: {filename}")
                
        return knowledge
    
    def get_combined_knowledge(self) -> str:
        """Get all knowledge combined as a single string
        
        Returns:
            Combined knowledge content
        """
        knowledge = self.load_all_knowledge()
        
        combined = []
        for key, content in knowledge.items():
            combined.append(f"=== {key.upper().replace('_', ' ')} ===\n")
            combined.append(content)
            combined.append("\n\n")
            
        return "\n".join(combined)
    
    def get_knowledge_by_type(self, knowledge_type: str) -> str:
        """Get specific knowledge by type
        
        Args:
            knowledge_type: Type of knowledge to retrieve
            
        Returns:
            Knowledge content or empty string if not found
        """
        knowledge = self.load_all_knowledge()
        return knowledge.get(knowledge_type, "")
    
    def search_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """Search across all knowledge sources
        
        Args:
            query: Search query
            
        Returns:
            List of matching sections with context
        """
        query_lower = query.lower()
        results = []
        
        knowledge = self.load_all_knowledge()
        
        for source, content in knowledge.items():
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if query_lower in line.lower():
                    # Get context (2 lines before and after)
                    start = max(0, i - 2)
                    end = min(len(lines), i + 3)
                    context = '\n'.join(lines[start:end])
                    
                    results.append({
                        'source': source,
                        'line_number': i + 1,
                        'matched_line': line,
                        'context': context
                    })
                    
        return results


# Singleton instance
_knowledge_loader = None


def get_knowledge_loader() -> KnowledgeLoader:
    """Get singleton knowledge loader instance"""
    global _knowledge_loader
    if _knowledge_loader is None:
        _knowledge_loader = KnowledgeLoader()
    return _knowledge_loader


def get_knowledge_for_crew() -> str:
    """Get formatted knowledge for CrewAI crew configuration
    
    Returns:
        Combined knowledge string for crew context
    """
    loader = get_knowledge_loader()
    return loader.get_combined_knowledge()