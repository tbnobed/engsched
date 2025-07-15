import os
import sys
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

def test_sendgrid():
    """Test SendGrid email sending"""
    print("Testing SendGrid email sending...")
    
    # Check if SendGrid API key exists
    api_key = os.environ.get('SENDGRID_API_KEY')
    if not api_key:
        print("ERROR: SendGrid API key is not set in environment variables")
        sys.exit(1)
        
    # Print the first few characters of the API key to confirm it exists
    key_preview = api_key[:4] + '...' if len(api_key) > 4 else '***'
    print(f"Using API key starting with: {key_preview}")
    
    # Create message
    message = Mail(
        from_email='alerts@obedtv.com',
        to_emails='alerts@obedtv.com',  # Using the admin email
        subject='SendGrid Test Email',
        html_content='<p>This is a test email sent from the OBE TV application.</p>'
    )
    
    try:
        # Initialize the SendGrid client
        print("Initializing SendGrid client...")
        sg = SendGridAPIClient(api_key)
        
        # Send the message
        print("Sending email...")
        response = sg.send(message)
        
        # Print response details
        print(f"Response status code: {response.status_code}")
        print(f"Response body: {response.body}")
        print(f"Response headers: {response.headers}")
        
        if response.status_code == 202:
            print("SUCCESS: Email sent successfully!")
        else:
            print(f"ERROR: Failed to send email. Status code: {response.status_code}")
            
    except Exception as e:
        print(f"EXCEPTION: {str(e)}")
        
if __name__ == "__main__":
    test_sendgrid()