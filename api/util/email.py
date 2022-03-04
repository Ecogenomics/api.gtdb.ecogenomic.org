import smtplib
from email.message import EmailMessage
from typing import List

from api.config import SMTP_USER, SMTP_SERV, SMTP_FROM, SMTP_PORT, SMTP_TIMEOUT, SMTP_PASS
import aiosmtplib


async def send_smtp_email(content: str, subject: str, to: List[str]):
    try:
        msg = EmailMessage()
        msg.set_content(content)
        msg['Subject'] = subject
        msg['From'] = SMTP_FROM
        msg['To'] = to
        # s = smtplib.SMTP(host=SMTP_SERV,
        #                  port=SMTP_PORT,
        #                  timeout=SMTP_TIMEOUT)
        # s.login(user=SMTP_USER,
        #         password=SMTP_PASS)
        # s.send_message(msg)
        # s.quit()
        await aiosmtplib.send(msg, hostname=SMTP_SERV, port=SMTP_PORT,
                              username=SMTP_USER, password=SMTP_PASS)
    except Exception as e:
        print(f'Exception sending SMTP e-mail: {e}')
        raise
