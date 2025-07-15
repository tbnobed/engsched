# Email-to-Ticket System Setup Guide

## Overview

The application now supports converting emails to tickets automatically using SendGrid's Inbound Parse webhook feature. When someone sends an email to any address ending in `@mail1.opscal.io`, it will automatically create a support ticket.

## SendGrid Configuration

### 1. Inbound Parse Settings

In your SendGrid dashboard:

1. Navigate to **Settings** → **Inbound Parse**
2. Click **Add Host & URL**
3. Configure:
   - **Subdomain**: `mail1.opscal.io`
   - **Destination URL**: `https://your-app-domain.com/api/inbound-email`
   - **Check spam**: ✅ Enabled (recommended)
   - **POST the raw, full MIME message**: ✅ Enabled (for attachments)

### 2. DNS Configuration

Add these DNS records to your domain:

**MX Record (for receiving emails):**
```
Type: MX
Host: mail1.opscal.io (or mail2.opscal.io)
Value: mx.sendgrid.net
Priority: 10
TTL: 300
```

**DMARC Record (to prevent blocking by Gmail/Outlook):**
```
Type: TXT
Host: _dmarc.opscal.io
Value: v=DMARC1; p=none; rua=mailto:admin@opscal.io
TTL: 300
```

**SPF Record (to authorize SendGrid to send for your domain):**
```
Type: TXT
Host: opscal.io
Value: v=spf1 include:sendgrid.net ~all
TTL: 300
```

**Note:** If you already have an SPF record, add `include:sendgrid.net` to it instead of creating a new one.

### 3. SendGrid Domain Authentication

To prevent DMARC blocking (like Gmail is doing), you must authenticate your domain in SendGrid:

1. **Go to SendGrid → Settings → Sender Authentication**
2. **Click "Authenticate Your Domain"**
3. **Enter your domain:** `opscal.io`
4. **Select "Yes" for advanced settings**
5. **Use these settings:**
   - Use automated security: Yes
   - Use custom return path: Yes (recommended)
   - Use custom bounce subdomain: Yes (recommended)
6. **Add the provided DNS records to your domain**
7. **Verify the domain in SendGrid**

**Important:** Without domain authentication, Gmail, Outlook, and other providers will block your emails due to DMARC policies.

## How It Works

### Email Processing Flow

1. **Email Received**: Email sent to `tickets@mail1.opscal.io` (or any address)
2. **SendGrid Processing**: SendGrid receives email and posts data to webhook
3. **Reply Detection**: System checks if email subject contains `[Ticket #ID]` pattern
   - **If Reply**: Adds comment to existing ticket and sends notifications
   - **If New**: Creates new ticket with details below
4. **Ticket Creation** (for new emails): App processes email and creates ticket with:
   - **Title**: Email subject line
   - **Description**: Email body content with sender info
   - **Category**: First available ticket category
   - **Priority**: Medium (default)
   - **Status**: Open
   - **Created By**: Existing user (if email matches) or system

### Reply Handling

When someone replies to a ticket confirmation email:
- **Subject Detection**: System looks for `[Ticket #123]` in subject line
- **Comment Addition**: Reply content is added as a comment to the existing ticket  
- **Notifications**: All assigned technicians, admins, and external users receive email notifications
- **User Recognition**: Internal users are credited as commenters, external users noted as external replies

**Example Reply Flow:**
1. Customer emails `support@mail1.opscal.io` with "Website is down"
2. System creates Ticket #45 and sends confirmation: `[Ticket #45] - Website is down`
3. Customer replies to confirmation email with additional details
4. SendGrid receives reply and posts to webhook (subject still contains `[Ticket #45]`)
5. System detects reply pattern and adds customer's message as a comment to Ticket #45
6. All technicians and the customer receive notification emails about the new comment
7. Technician can reply through the web interface, and customer gets notified
8. Customer can continue replying via email, maintaining the conversation thread admin

### Advanced Email Handling

The system includes intelligent parsing for different email types:

**Raw MIME Processing**: Handles SendGrid's "POST the raw, full MIME message" format with proper parsing
**Text and HTML Emails**: Prefers plain text, falls back to HTML with tag removal  
**Multipart Messages**: Correctly processes multipart MIME emails with different content types
**Forwarded Emails**: Detects Fw:/Fwd: subjects and attempts to extract original content
**Empty Content**: Captures metadata from headers, envelope, and attachment info when body is empty
**User Recognition**: Assigns tickets to known users, creates under admin for unknown senders
**Encoding Support**: Handles UTF-8 character encoding with error tolerance

### Supported Email Addresses

Any address ending in `@mail1.opscal.io` will work:
- `tickets@mail1.opscal.io`
- `support@mail1.opscal.io`
- `help@mail1.opscal.io`
- `emergency@mail1.opscal.io`

### User Recognition

- **Known Users**: If sender email matches existing user, ticket is assigned to them
- **Unknown Senders**: Ticket created without assignment, admin can assign later
- **Confirmation**: Known users receive confirmation email with ticket number

### Reply Threading

The system supports intelligent email reply detection with consistent subject line formatting:

- **Reply Detection**: System detects replies using "[Ticket #ID]" pattern in subject lines
- **Automatic Comments**: Reply emails become comments on existing tickets instead of new tickets
- **Consistent Threading**: ALL email notifications use "[Ticket #ID]" prefix format:
  - **Ticket Creation**: `[Ticket #14] - Hello, who can help me`
  - **Assignment**: `[Ticket #14] - Hello, who can help me (Assigned)`
  - **Comments**: `[Ticket #14] - Hello, who can help me (New Comment)`
  - **Status Changes**: `[Ticket #14] - Hello, who can help me (Status: In Progress)`
- **Perfect Threading**: Replies to assignments, comments, or status updates all stay in same ticket conversation

## Testing the System

### Admin Test Endpoint

Visit `/api/test-email-webhook` (admin only) to create a test ticket and verify the system is working.

### Manual Testing

Send a test email to `test@mail1.opscal.io` from any email client:

```
To: test@mail1.opscal.io
Subject: Test Ticket Creation
Body: This is a test email to verify the email-to-ticket system.
```

Check the tickets section to see if it was created successfully.

## Troubleshooting

### Common Issues

1. **DNS Propagation**: MX record changes can take up to 48 hours to propagate
2. **Webhook URL**: Ensure your app URL is accessible from the internet
3. **HTTPS Required**: SendGrid requires HTTPS for webhook URLs
4. **Ticket Categories**: Ensure at least one ticket category exists in the system

### Debug Information

Check application logs for email processing details:
- Incoming webhook calls are logged with sender and subject
- Ticket creation success/failure is logged
- Confirmation email sending status is logged

### Testing Webhook Connectivity

Use curl to test the webhook endpoint:

```bash
curl -X POST https://your-app-domain.com/api/inbound-email \
  -d "from=test@example.com" \
  -d "subject=Test Subject" \
  -d "text=Test message body" \
  -d "to=tickets@mail1.opscal.io"
```

## Security Considerations

- Webhook endpoint accepts POST requests from any source (SendGrid requirement)
- Email content is sanitized before ticket creation
- Only basic email fields are processed (from, subject, text, html)
- No executable attachments are processed
- Spam filtering should be enabled in SendGrid settings

## Future Enhancements

Potential improvements for the email-to-ticket system:
- Attachment handling and storage
- Email threading for ticket updates
- Priority detection from email keywords
- Category assignment based on email address or subject
- Auto-assignment rules based on sender domain