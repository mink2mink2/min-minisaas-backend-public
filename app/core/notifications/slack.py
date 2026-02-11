"""Slack notifier utility for security alerts"""
from typing import Optional, Dict, Any
import httpx
from app.core.config import settings


class SlackNotifier:
    """Send security alerts to Slack via Incoming Webhook.

    - No-op when SLACK_WEBHOOK_URL is not configured.
    - Designed for fire-and-forget usage; failures won't break main flow.
    """

    @staticmethod
    async def send_security_alert(
        event_type: str,
        user_id: Optional[str] = None,
        severity: str = "LOW",
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        webhook = settings.SLACK_WEBHOOK_URL
        if not webhook:
            return  # Monitoring disabled

        # Build message payload
        title = f":rotating_light: Security Alert: {event_type}"
        fields = []
        if user_id:
            fields.append({"type": "mrkdwn", "text": f"*User*: `{user_id}`"})
        if severity:
            fields.append({"type": "mrkdwn", "text": f"*Severity*: `{severity}`"})
        if ip_address:
            fields.append({"type": "mrkdwn", "text": f"*IP*: `{ip_address}`"})
        if user_agent:
            fields.append({"type": "mrkdwn", "text": f"*UA*: `{user_agent[:150]}`"})

        # Condense details to a short code block if present
        details_text = None
        if details:
            try:
                # Keep payload small
                import json
                snippet = json.dumps(details)[:700]
                details_text = f"```{snippet}```"
            except Exception:
                pass

        payload = {
            "text": title,
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": title}},
                {"type": "section", "fields": fields} if fields else None,
                {"type": "section", "text": {"type": "mrkdwn", "text": details_text}},
            ],
        }
        # Remove None blocks
        payload["blocks"] = [b for b in payload["blocks"] if b]

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(webhook, json=payload)
        except Exception as e:
            # Do not raise; just log to stdout/stderr
            print(f"[SlackNotifier] Failed to send alert: {e}")


slack_notifier = SlackNotifier()
