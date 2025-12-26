import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

log = logging.getLogger(__name__)

def send_email(subject, body, to_email, from_email, smtp_server, smtp_port, smtp_user, smtp_password):
    """
    Sends an email using the provided SMTP server details.
    """
    if not all([from_email, to_email, smtp_server, smtp_port, smtp_user, smtp_password]):
        log.error("Missing one or more SMTP configuration parameters. Cannot send email.")
        return

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        # Connect to the SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Upgrade connection to secure TLS
        server.login(smtp_user, smtp_password)
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        server.quit()
        log.info(f"Email sent successfully to {to_email}")
    except Exception as e:
        log.error(f"Failed to send email to {to_email}: {e}")
