import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class DeduplicationService:
    """Handle duplicate detection and management"""
    
    @staticmethod
    def generate_content_hash(content: str, url: str = "") -> str:
        """Generate SHA256 hash of content for deduplication"""
        combined = content + url
        return hashlib.sha256(combined.encode()).hexdigest()
    
    @staticmethod
    def calculate_content_similarity(text1: str, text2: str) -> float:
        """Calculate similarity between two texts (0-1)"""
        if not text1 or not text2:
            return 0.0
        
        set1 = set(text1.lower().split())
        set2 = set(text2.lower().split())
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    @staticmethod
    def detect_significant_changes(
        old_content: str,
        new_content: str,
        similarity_threshold: float = 0.85
    ) -> Dict[str, Any]:
        """
        Detect if content has changed significantly
        Returns info about the change
        """
        similarity = DeduplicationService.calculate_content_similarity(old_content, new_content)
        
        is_significant = similarity < similarity_threshold
        
        return {
            "is_significant": is_significant,
            "similarity_score": round(similarity, 3),
            "old_hash": DeduplicationService.generate_content_hash(old_content),
            "new_hash": DeduplicationService.generate_content_hash(new_content),
            "change_type": "content_update" if is_significant else "no_change",
            "detected_at": datetime.utcnow().isoformat()
        }
