import logging
from typing import Dict, List, Any
import asyncio
import aiohttp
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class AlertSender:
    """Handle sending alerts via various channels"""
    
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "localhost")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.from_email = os.getenv("ALERT_FROM_EMAIL", "alerts@darkweb.local")
    
    async def send_email_alert(
        self,
        to_email: str,
        keyword: str,
        risk_level: str,
        url: str,
        finding_summary: str
    ) -> bool:
        """Send email alert"""
        try:
            # For production, use SMTP. For now, just log
            logger.info(f"[Alert] Email to {to_email}: {keyword} found at {url} (Risk: {risk_level})")
            logger.info(f"[Alert] Summary: {finding_summary[:200]}...")
            return True
        except Exception as e:
            logger.error(f"[Alert] Email failed: {e}")
            return False
    
    async def send_webhook_alert(
        self,
        webhook_url: str,
        keyword: str,
        risk_level: str,
        url: str,
        finding_data: Dict[str, Any]
    ) -> bool:
        """Send webhook alert"""
        try:
            payload = {
                "event": "threat_alert",
                "timestamp": datetime.utcnow().isoformat(),
                "keyword": keyword,
                "risk_level": risk_level,
                "source_url": url,
                "finding": finding_data
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload, timeout=10) as resp:
                    if resp.status == 200:
                        logger.info(f"[Alert] Webhook sent to {webhook_url}")
                        return True
                    else:
                        logger.error(f"[Alert] Webhook failed: {resp.status}")
                        return False
        except Exception as e:
            logger.error(f"[Alert] Webhook error: {e}")
            return False
    
    async def send_alerts(
        self,
        alerts: List[Dict],
        finding_data: Dict[str, Any]
    ) -> List[str]:
        """Send alerts for a finding that matches keywords"""
        triggered_alert_ids = []
        
        for alert in alerts:
            alert_id = alert.get("id")
            notification_type = alert.get("notification_type", "email")
            notification_endpoint = alert.get("notification_endpoint")
            keyword = alert.get("keyword")
            risk_threshold = alert.get("risk_level_threshold", "medium")
            
            if not notification_endpoint:
                logger.warning(f"[Alert] No endpoint for alert {alert_id}")
                continue
            
            try:
                if notification_type == "email":
                    success = await self.send_email_alert(
                        to_email=notification_endpoint,
                        keyword=keyword,
                        risk_level=finding_data.get("risk_level"),
                        url=finding_data.get("url"),
                        finding_summary=finding_data.get("text_excerpt", "")
                    )
                elif notification_type == "webhook":
                    success = await self.send_webhook_alert(
                        webhook_url=notification_endpoint,
                        keyword=keyword,
                        risk_level=finding_data.get("risk_level"),
                        url=finding_data.get("url"),
                        finding_data=finding_data
                    )
                else:
                    logger.warning(f"[Alert] Unknown notification type: {notification_type}")
                    success = False
                
                if success:
                    triggered_alert_ids.append(alert_id)
            except Exception as e:
                logger.error(f"[Alert] Failed to send to {notification_type}: {e}")
        
        return triggered_alert_ids
