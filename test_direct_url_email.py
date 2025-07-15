import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

def test_direct_url_email():
    """Test email sending with a direct URL (no Flask url_for)"""
    print("Testing email with direct URL...")
    
    # Check for API key
    api_key = os.environ.get('SENDGRID_API_KEY')
    if not api_key:
        print("ERROR: SendGrid API key is not set in environment variables")
        return
        
    # Use a hardcoded URL
    tickets_url = "http://localhost:5000/tickets"
    print(f"Using direct URL: {tickets_url}")
        
    # Create message with the URL
    message = Mail(
        from_email='alerts@obedtv.com',
        to_emails='alerts@obedtv.com',
        subject='Direct URL Test Email',
        html_content=f'<p>This is a test email with a direct URL: <a href="{tickets_url}">View Tickets</a></p>'
    )
    
    try:
        # Initialize SendGrid client
        sg = SendGridAPIClient(api_key)
        
        # Send message
        print("Sending email...")
        response = sg.send(message)
        
        # Check response
        if response.status_code == 202:
            print("SUCCESS: Email sent successfully!")
        else:
            print(f"ERROR: Failed to send email. Status code: {response.status_code}")
            
    except Exception as e:
        print(f"EXCEPTION: {str(e)}")
        
if __name__ == "__main__":
    test_direct_url_email()