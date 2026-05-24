"""
Email notification service.

Providers (free tiers):
  - resend  — Resend.com (100 emails/day free, easiest setup)
  - smtp    — Any SMTP (e.g. Brevo 300/day free, Gmail app password)
"""
import logging
import smtplib
import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import List, Dict

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


def _is_placeholder(value: str, placeholders: tuple) -> bool:
    v = (value or "").strip().lower()
    if not v:
        return True
    return any(p in v for p in placeholders)


def is_email_configured() -> bool:
    """True when a supported email provider is configured with a valid sender."""
    sender = (settings.alert_from_email or "").strip()
    if _is_placeholder(sender, ("demo@", "yourdomain", "example.com", "you@")):
        return False

    provider = settings.effective_email_provider
    if provider == "resend":
        key = (settings.resend_api_key or "").strip()
        return bool(key) and not _is_placeholder(key, ("re_demo", "your_resend", "re_xxx"))
    if provider == "smtp":
        return bool(
            settings.smtp_host.strip()
            and settings.smtp_username.strip()
            and settings.smtp_password.strip()
        )
    return False


# Backward-compatible alias (removed SendGrid)
is_sendgrid_configured = is_email_configured


def resolve_alert_recipients(zone: Dict) -> List[str]:
    """Merge per-zone emails with global GLOBAL_ALERT_EMAILS (deduplicated)."""
    emails = []
    seen = set()
    for source in (zone.get("alert_emails") or [], settings.global_alert_emails_list):
        for email in source:
            e = (email or "").strip().lower()
            if e and e not in seen and "@" in e:
                seen.add(e)
                emails.append(email.strip())
    return emails


def _format_from_address() -> str:
    name = (settings.alert_from_name or "Foresence Alerts").strip()
    email = settings.alert_from_email.strip()
    return f"{name} <{email}>"


async def _send_via_resend(recipients: List[str], subject: str, html_content: str) -> int:
    payload = {
        "from": _format_from_address(),
        "to": recipients,
        "subject": subject,
        "html": html_content,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {settings.resend_api_key.strip()}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
    if response.status_code >= 400:
        detail = response.text[:500]
        raise RuntimeError(f"Resend API error ({response.status_code}): {detail}")
    return response.status_code


def _send_via_smtp_sync(recipients: List[str], subject: str, html_content: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = _format_from_address()
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    host = settings.smtp_host.strip()
    port = settings.smtp_port
    username = settings.smtp_username.strip()
    password = settings.smtp_password.strip()

    if settings.smtp_use_tls:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(username, password)
            server.sendmail(settings.alert_from_email.strip(), recipients, msg.as_string())
    else:
        with smtplib.SMTP_SSL(host, port, timeout=30) as server:
            server.login(username, password)
            server.sendmail(settings.alert_from_email.strip(), recipients, msg.as_string())


async def _send_via_smtp(recipients: List[str], subject: str, html_content: str) -> int:
    await asyncio.to_thread(_send_via_smtp_sync, recipients, subject, html_content)
    return 200


async def _send_html_email(recipients: List[str], subject: str, html_content: str) -> int:
    if not recipients:
        return 0
    if not is_email_configured():
        raise RuntimeError(
            "Email is not configured. Set RESEND_API_KEY + ALERT_FROM_EMAIL, "
            "or SMTP_HOST/SMTP_USERNAME/SMTP_PASSWORD (see backend/.env.example)."
        )

    provider = settings.effective_email_provider
    if provider == "smtp":
        return await _send_via_smtp(recipients, subject, html_content)
    return await _send_via_resend(recipients, subject, html_content)


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
    </div>
  </div>
</body>
</html>
"""


def _build_zone_health_report_html(zones_report: List[Dict], generated_at: datetime) -> str:
    rows_html = ""
    for z in zones_report:
        status = z.get("status", "unknown")
        status_color = {"healthy": "#16a34a", "warning": "#d97706", "critical": "#dc2626"}.get(
            status, "#64748b"
        )
        if z.get("latest_image_url"):
            img_block = (
                f'<img src="{z["latest_image_url"]}" alt="NDVI" '
                f'style="max-width:140px;border-radius:6px;border:1px solid #e2e8f0;" />'
            )
        else:
            img_block = '<span style="color:#94a3b8;font-size:12px;">No image yet</span>'

        rows_html += f"""
        <tr>
          <td style="padding:12px;border-bottom:1px solid #e2e8f0;font-weight:600;">{z.get("name", "—")}</td>
          <td style="padding:12px;border-bottom:1px solid #e2e8f0;">
            <span style="color:{status_color};font-weight:700;text-transform:uppercase;">{status}</span>
          </td>
          <td style="padding:12px;border-bottom:1px solid #e2e8f0;text-align:center;">{z.get("health_score", "—")}/100</td>
          <td style="padding:12px;border-bottom:1px solid #e2e8f0;">{z.get("area_ha", 0):.1f} ha</td>
          <td style="padding:12px;border-bottom:1px solid #e2e8f0;">{z.get("latest_ndvi", "—")}</td>
          <td style="padding:12px;border-bottom:1px solid #e2e8f0;">{z.get("new_alerts", 0)}</td>
          <td style="padding:12px;border-bottom:1px solid #e2e8f0;font-size:12px;color:#64748b;">{z.get("last_scanned", "Never")}</td>
          <td style="padding:12px;border-bottom:1px solid #e2e8f0;">{img_block}</td>
        </tr>
        """

    return f"""
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Foresence Zone Health Report</title></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f8fafc;margin:0;padding:24px;">
  <div style="max-width:900px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
    <div style="background:#0f172a;padding:28px 32px;color:#fff;">
      <h1 style="margin:0;font-size:22px;">🌿 Forest Monitoring Health Report</h1>
      <p style="margin:8px 0 0;opacity:0.85;font-size:14px;">Generated {generated_at.strftime("%Y-%m-%d %H:%M UTC")}</p>
    </div>
    <div style="padding:24px 32px;">
      <p style="color:#475569;font-size:14px;line-height:1.6;">
        Summary for <strong>{len(zones_report)}</strong> selected zone(s).
      </p>
      <table style="width:100%;border-collapse:collapse;margin-top:20px;font-size:13px;">
        <thead>
          <tr style="background:#f1f5f9;">
            <th style="padding:10px;text-align:left;">Zone</th>
            <th style="padding:10px;text-align:left;">Status</th>
            <th style="padding:10px;">Health</th>
            <th style="padding:10px;text-align:left;">Area</th>
            <th style="padding:10px;">Latest NDVI</th>
            <th style="padding:10px;">New alerts</th>
            <th style="padding:10px;text-align:left;">Last scan</th>
            <th style="padding:10px;">Latest NDVI map</th>
          </tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>
      <p style="margin-top:24px;text-align:center;">
        <a href="{settings.frontend_url}" style="display:inline-block;background:#16a34a;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600;">Open Dashboard</a>
      </p>
    </div>
  </div>
</body>
</html>
"""


async def send_zone_health_report_email(recipients: List[str], zones_report: List[Dict]) -> None:
    if not recipients:
        raise ValueError("No recipient email addresses provided")
    subject = f"🌿 Foresence Health Report — {len(zones_report)} zone(s)"
    html = _build_zone_health_report_html(zones_report, datetime.utcnow())
    status = await _send_html_email(recipients, subject, html)
    logger.info(
        f"Zone health report sent to {len(recipients)} recipients via {settings.effective_email_provider}. "
        f"Status: {status}"
    )


async def send_deforestation_alert_email(recipients: List[str], alert: Dict, zone: Dict) -> None:
    if not recipients:
        return
    if not settings.auto_email_on_alert:
        logger.info("Auto email on alert is disabled (AUTO_EMAIL_ON_ALERT=false)")
        return

    severity = alert.get("severity", "low")
    severity_upper = severity.upper()
    zone_name = alert.get("zone_name", zone.get("name", "Unknown"))
    severity_emoji = SEVERITY_EMOJIS.get(severity, "🔵")

    subject = f"{severity_emoji} [{severity_upper}] Deforestation Alert — {zone_name}"
    html_content = _build_html_email(alert, zone)

    try:
        status = await _send_html_email(recipients, subject, html_content)
        logger.info(
            f"Alert email sent to {len(recipients)} recipients for zone '{zone_name}' "
            f"via {settings.effective_email_provider}. Status: {status}"
        )
    except Exception as e:
        logger.error(f"Failed to send alert email for zone '{zone_name}': {e}", exc_info=True)
        raise
