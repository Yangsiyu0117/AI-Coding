"""Email notifier"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from notifiers.base import BaseNotifier


class EmailNotifier(BaseNotifier):
    """邮件通知"""

    def __init__(self, smtp_host, smtp_port, username, password, smtp_ssl=True):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.smtp_ssl = smtp_ssl

    def send(self, title, content, content_type="html", to_addr=None):
        msg = MIMEMultipart("alternative")
        msg["Subject"] = title
        msg["From"] = self.username
        msg["To"] = to_addr or self.username

        subtype = "html" if content_type == "html" else "plain"
        msg.attach(MIMEText(content, subtype, "utf-8"))

        if self.smtp_ssl:
            server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=15)
        else:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15)
            server.starttls()

        if self.username and self.password:
            server.login(self.username, self.password)
        server.sendmail(self.username, to_addr or self.username, msg.as_string())
        server.quit()

    def send_report(self, report_html, report_markdown=None, format_type="html"):
        """Send inspection report as email"""
        content = report_html if format_type == "html" else (report_markdown or report_html)
        return self.send("运维巡检报告", content, format_type)