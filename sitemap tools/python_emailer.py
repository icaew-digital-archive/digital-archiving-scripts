import subprocess
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Function to call the other script with arguments and capture its output
def run_script_and_get_output(script_path, script_args):
    try:
        # Run the script with the provided arguments and capture its output
        result = subprocess.run(['python3', script_path] + script_args, capture_output=True, text=True)
        return result.stdout, result.stderr
    except Exception as e:
        return "", str(e)

# Function to send an email
def send_email(from_email, from_password, to_email, cc_emails, subject, body):
    try:
        # Set up the email content
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Cc'] = ", ".join(cc_emails)  # Add CC recipients
        msg['Subject'] = subject

        # Attach the body text
        msg.attach(MIMEText(body, 'plain'))

        # Combine To and CC recipients for the send call
        all_recipients = [to_email] + cc_emails

        # Set up the SMTP server
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()  # Secure the connection
            server.login(from_email, from_password)
            server.send_message(msg, to_addrs=all_recipients)
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

# Main logic
if __name__ == "__main__":
    # Path to your existing script
    script_path = 'sitemap_monitor.py'

    # Arguments for the script
    script_args = [
        '--sitemap',
        'https://www.icaew.com/sitemap_corporate.xml',
        'https://www.icaew.com/sitemap_careers.xml',
        '--outputnew'
    ]

    # Run the script and get its output
    stdout, stderr = run_script_and_get_output(script_path, script_args)

    # Hardcoded email credentials and recipient
    from_email = ""
    from_password = "" # This is the "App password"
    to_email = ""
    cc_emails = [""]  # Add CC recipients here

    # Prepare email subject and body
    subject = "New pages found in sitemap"
    body = "Script Output:\n\n" + stdout
    if stderr:
        body += "\n\nErrors:\n" + stderr

    # Send the email
    send_email(from_email, from_password, to_email, cc_emails, subject, body)

