import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate

# Email configuration
def send_test_email():
    try:
        # Create message
        msg = MIMEText('LIEBI')
        msg['Subject'] = 'hallo mein lieber Schummel'
        msg['From'] = '[EMAIL_PLACEHOLDER]'
        msg['To'] = '[EMAIL_PLACEHOLDER]'
        msg['Date'] = formatdate(localtime=True)

        # Connect and send
        with smtplib.SMTP_SSL('mail.abydon.com', 465) as server:
            server.login('[EMAIL_PLACEHOLDER]', 'a4gBH@#oqvbQxnUBWqA62DJ^KGR4YXFKGHy@cm^TUh8%j6oZK9n6wnw')
            server.send_message(msg)

        return {'status': 'success', 'message': 'Testmail erfolgreich gesendet'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

if __name__ == '__main__':
    print(send_test_email())