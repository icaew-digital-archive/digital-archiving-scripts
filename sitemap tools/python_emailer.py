import base64
import json
import os
import subprocess
import sys
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Function to call the other script with arguments and capture its output
def run_script_and_get_output(script_path, script_args):
    try:
        # Run the script with the provided arguments and capture its output
        # Run from the script's own folder so sitemap_memory.json is found regardless of cron's cwd
        result = subprocess.run([sys.executable, script_path] + script_args, capture_output=True, text=True,
                                cwd=os.path.dirname(script_path))
        return result.stdout, result.stderr
    except Exception as e:
        return "", str(e)

# Function to get a short-lived Gmail API access token from the saved refresh token
def get_access_token(token_path):
    with open(token_path) as f:
        token = json.load(f)
    response = requests.post('https://oauth2.googleapis.com/token', data={
        'client_id': token['client_id'],
        'client_secret': token['client_secret'],
        'refresh_token': token['refresh_token'],
        'grant_type': 'refresh_token',
    }, timeout=30)
    response.raise_for_status()
    return response.json()['access_token']

# Function to send an email via the Gmail API (HTTPS, as DigitalOcean blocks SMTP ports)
def send_email(from_email, token_path, to_email, cc_emails, subject, body):
    try:
        # Set up the email content
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        if cc_emails:
            msg['Cc'] = ", ".join(cc_emails)  # Add CC recipients
        msg['Subject'] = subject

        # Attach the body text
        msg.attach(MIMEText(body, 'plain'))

        # Gmail sends to everyone in the To and Cc headers
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        response = requests.post(
            'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
            headers={'Authorization': f'Bearer {get_access_token(token_path)}'},
            json={'raw': raw},
            timeout=30,
        )
        response.raise_for_status()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

# Main logic
if __name__ == "__main__":
    # Path to your existing script
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sitemap_monitor.py')

    # Arguments for the script
    script_args = [
        '--sitemap',
        'https://www.icaew.com/sitemap_corporate.xml',
        '--show-new'
    ]

    # Run the script and get its output
    stdout, stderr = run_script_and_get_output(script_path, script_args)

    # Hardcoded email credentials and recipient
    from_email = ""
    token_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gmail_token.json')  # Created by gmail_authorise.py
    to_email = ""
    cc_emails = []  # Add CC recipients here, e.g. ["a@example.com"]

    # Prepare email subject and body
    subject = "New pages found in sitemap"
    body = "Script Output:\n\n" + stdout
    if stderr:
        body += "\n\nErrors:\n" + stderr

    # Send the email
    send_email(from_email, token_path, to_email, cc_emails, subject, body)
