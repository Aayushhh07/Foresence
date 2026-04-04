"""
SendGrid email notification service.
Sends HTML deforestation alert emails to zone-configured recipients.
"""
import logging
from datetime import datetime
from typing import List, Dict

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, To, From, Content

from app.core.config import settings

logger = logging.getLogger(__name__)

SEVERITY_COLORS = {
    "critical": "#dc2626",
    "high": "#ea580c",
    "medium": "#d97706",
    "low": "#2563eb",
}

SEVERITY_EMOJIS = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🔵",
}


def _build_html_email(alert: Dict, zone: Dict) -> str:
    """Build the HTML email body for a deforestation alert."""
    severity = alert.get("severity", "low")
    severity_color = SEVERITY_COLORS.get(severity, "#2563eb")
    severity_emoji = SEVERITY_EMOJIS.get(severity, "🔵")

    detected_at = alert.get("detected_at", datetime.utcnow())
    if isinstance(detected_at, datetime):
        detected_str = detected_at.strftime("%Y-%m-%d %H:%M UTC")
    else:
        detected_str = str(detected_at)

    ndvi_before = alert.get("ndvi_before", 0.0)
    ndvi_after = alert.get("ndvi_after", 0.0)
    ndvi_delta = alert.get("ndvi_delta", 0.0)
    confidence = alert.get("confidence", 0.0)
    change_area_ha = alert.get("change_area_ha", 0.0)
    change_map_url = alert.get("change_map_url", "#")
    zone_name = alert.get("zone_name", zone.get("name", "Unknown"))
    frontend_url = settings.frontend_url
    alert_id = str(alert.get("_id", ""))

    ndvi_delta_color = "#dc2626" if ndvi_delta < 0 else "#16a34a"
    ndvi_delta_sign = "▼" if ndvi_delta < 0 else "▲"

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Deforestation Alert — {zone_name}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
           margin: 0; padding: 0; background: #f8fafc; color: #1e293b; }}
    .container {{ max-width: 600px; margin: 0 auto; background: #ffffff;
                  border-radius: 12px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.08); }}
    .header {{ background: {severity_color}; padding: 32px 40px; text-align: center; }}
    .header h1 {{ color: white; margin: 0; font-size: 24px; font-weight: 700; }}
    .header p {{ color: rgba(255,255,255,0.85); margin: 8px 0 0; font-size: 14px; }}
    .severity-badge {{ display: inline-block; background: rgba(255,255,255,0.2);
                       color: white; padding: 4px 12px; border-radius: 20px;
                       font-size: 13px; font-weight: 600; margin-top: 12px; }}
    .body {{ padding: 32px 40px; }}
    .stat-row {{ display: flex; gap: 16px; margin: 24px 0; }}
    .stat-card {{ flex: 1; background: #f8fafc; border-radius: 8px; padding: 16px;
                  border: 1px solid #e2e8f0; text-align: center; }}
    .stat-label {{ font-size: 11px; color: #64748b; text-transform: uppercase;
                   letter-spacing: 0.05em; margin-bottom: 6px; }}
    .stat-value {{ font-size: 22px; font-weight: 700; color: #0f172a; }}
    .ndvi-section {{ background: #f1f5f9; border-radius: 8px; padding: 20px; margin: 20px 0; }}
    .ndvi-row {{ display: flex; justify-content: space-between; align-items: center;
                 margin: 8px 0; }}
    .ndvi-label {{ font-size: 13px; color: #475569; }}
    .ndvi-value {{ font-size: 16px; font-weight: 600; }}
    .ndvi-delta {{ color: {ndvi_delta_color}; font-size: 18px; font-weight: 700; }}
    .map-section {{ text-align: center; margin: 24px 0; }}
    .map-img {{ max-width: 100%; border-radius: 8px;
                border: 2px solid #e2e8f0; }}
    .btn {{ display: inline-block; background: #16a34a; color: white;
            padding: 12px 28px; border-radius: 8px; text-decoration: none;
            font-weight: 600; font-size: 14px; margin: 16px 0; }}
    .footer {{ background: #0f172a; padding: 20px 40px; text-align: center; }}
    .footer p {{ color: #64748b; font-size: 12px; margin: 4px 0; }}
    .footer span {{ color: #16a34a; font-weight: 600; }}
    .confidence-bar {{ width: 100%; height: 8px; background: #e2e8f0;
                        border-radius: 4px; overflow: hidden; margin: 6px 0; }}
    .confidence-fill {{ height: 100%; background: {severity_color};
                         width: {int(confidence * 100)}%; border-radius: 4px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>{severity_emoji} Deforestation Alert Detected</h1>
      <p>Zone: <strong>{zone_name}</strong></p>
      <p>Detected at {detected_str}</p>
      <div class="severity-badge">{severity.upper()} SEVERITY</div>
    </div>

    <div class="body">
      <div class="stat-row">
        <div class="stat-card">
          <div class="stat-label">Area Affected</div>
          <div class="stat-value">{change_area_ha:.1f} ha</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Confidence</div>
          <div class="stat-value">{int(confidence * 100)}%</div>
          <div class="confidence-bar">
            <div class="confidence-fill"></div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">NDVI Change</div>
          <div class="stat-value ndvi-delta">{ndvi_delta_sign} {abs(ndvi_delta):.3f}</div>
        </div>
      </div>

      <div class="ndvi-section">
        <h3 style="margin:0 0 12px; font-size:14px; color:#475569; text-transform:uppercase; letter-spacing:0.05em;">
          Vegetation Index Comparison
        </h3>
        <div class="ndvi-row">
          <span class="ndvi-label">NDVI Before</span>
          <span class="ndvi-value" style="color:#16a34a;">{ndvi_before:.4f}</span>
        </div>
        <div class="ndvi-row">
          <span class="ndvi-label">NDVI After</span>
          <span class="ndvi-value" style="color:{ndvi_delta_color};">{ndvi_after:.4f}</span>
        </div>
        <div class="ndvi-row" style="border-top:1px solid #cbd5e1;padding-top:8px;margin-top:8px;">
          <span class="ndvi-label">Delta</span>
          <span class="ndvi-delta">{ndvi_delta:+.4f}</span>
        </div>
      </div>

      <div class="map-section">
        <p style="font-size:13px;color:#64748b;margin-bottom:12px;">Change Detection Map</p>
        <a href="{change_map_url}" target="_blank">
          <img src="{change_map_url}" alt="Change Detection Map" class="map-img" />
        </a>
        <p style="font-size:11px;color:#94a3b8;margin-top:8px;">
          Red = vegetation loss · Green = vegetation gain · Gray = no change
        </p>
      </div>

      <div style="text-align:center;">
        <a href="{frontend_url}/alerts" class="btn">
          View in Dashboard →
        </a>
      </div>
    </div>

    <div class="footer">
      <p>This alert was generated automatically by <span>Foresence</span></p>
      <p>Zone: {zone_name} · Alert ID: {alert_id}</p>
      <p style="margin-top:8px;font-size:11px;">
        To stop receiving alerts for this zone, update your notification settings
        in the dashboard.
      </p>
    </div>
  </div>
</body>
</html>
"""


async def send_deforestation_alert_email(
    recipients: List[str],
    alert: Dict,
    zone: Dict,
) -> None:
    """
    Send a deforestation alert email to all configured recipients.
    Uses SendGrid API.
    """
    if not recipients:
        return

    severity = alert.get("severity", "low")
    severity_upper = severity.upper()
    zone_name = alert.get("zone_name", zone.get("name", "Unknown"))
    severity_emoji = SEVERITY_EMOJIS.get(severity, "🔵")

    subject = f"{severity_emoji} [{severity_upper}] Deforestation Alert — {zone_name}"
    html_content = _build_html_email(alert, zone)

    try:
        sg = SendGridAPIClient(settings.sendgrid_api_key)
        message = Mail(
            from_email=From(settings.alert_from_email, "Foresence Alerts"),
            to_emails=[To(email) for email in recipients],
            subject=subject,
            html_content=Content("text/html", html_content),
        )
        response = sg.send(message)
        logger.info(
            f"Alert email sent to {len(recipients)} recipients for zone '{zone_name}'. "
            f"SendGrid status: {response.status_code}"
        )
    except Exception as e:
        logger.error(
            f"Failed to send alert email for zone '{zone_name}': {e}", exc_info=True
        )
        raise
