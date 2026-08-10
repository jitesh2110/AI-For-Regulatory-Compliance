import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'recipients.json')

def load_recipients():
    if not os.path.exists(DB_PATH):
        return []
    try:
        with open(DB_PATH, 'r') as f:
            return json.load(f)
    except:
        return []

def save_recipients(recipients):
    with open(DB_PATH, 'w') as f:
        json.dump(recipients, f, indent=4)

def add_recipient(email):
    recipients = load_recipients()
    if email not in recipients:
        recipients.append(email)
        save_recipients(recipients)
        return True
    return False

def remove_recipient(email):
    recipients = load_recipients()
    if email in recipients:
        recipients.remove(email)
        save_recipients(recipients)
        return True
    return False

def update_recipient(old_email, new_email):
    recipients = load_recipients()
    if old_email in recipients:
        index = recipients.index(old_email)
        if new_email not in recipients:
            recipients[index] = new_email
            save_recipients(recipients)
            return True, "Recipient updated successfully."
        else:
            return False, "New email already exists."
    return False, "Old email not found."

def send_compliance_email(docx_bytes, filename):
    recipients = load_recipients()
    if not recipients:
        print("No recipients configured.")
        return 0
        
    sender_email = 'jsnewth@gmail.com'
    sender_password = 'qrrc tibt icph shjo'
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = "Undisclosed Recipients" # Bcc is better for lists, but standard To string works too for simple case. Let's send individually or together.
    msg['Subject'] = f'Compliance Memo: {filename}'
    
    body = "Hello Team,\n\nPlease find the latest updated Compliance Audit Memo attached for your review.\n\n- RegAI"
    msg.attach(MIMEText(body, 'plain'))
    
    part = MIMEApplication(docx_bytes, Name=filename)
    part['Content-Disposition'] = f'attachment; filename="{filename}"'
    msg.attach(part)
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        # Sending to list
        server.sendmail(sender_email, recipients, text)
        server.quit()
        print(f"Successfully sent email to {len(recipients)} recipients.")
        return len(recipients)
    except Exception as e:
        print(f"Failed to send email: {e}")
        raise e
