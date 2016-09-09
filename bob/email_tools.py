import smtplib
from email.mime.text import MIMEText
from bob.settings import get_email_settings


def send_email(to_address, subject, body):

    settings = get_email_settings()
    if not settings:
        return

    server = smtplib.SMTP(settings['host'], settings['port'])

    if 'debug' in settings:
        server.set_debuglevel(bool(settings['debug']))

    if 'starttls' in settings and settings['starttls']:
        server.ehlo()
        server.starttls()

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = settings['from']
    msg['To'] = ','.join(to_address)

    server.login(settings['login'], settings['password'])
    server.sendmail(settings['from'], to_address, msg.as_string())
    server.quit()
