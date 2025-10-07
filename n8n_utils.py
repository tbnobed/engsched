import os
import requests
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

def send_ticket_to_n8n(ticket_id: int, title: str, description: str) -> Optional[str]:
    """
    Send ticket information to n8n webhook for AI analysis
    
    Args:
        ticket_id: The ticket ID
        title: The ticket title
        description: The ticket description
        
    Returns:
        The AI-generated response text, or None if the request fails
    """
    webhook_url = os.environ.get('N8N_WEBHOOK_URL')
    
    if not webhook_url:
        logger.warning("N8N_WEBHOOK_URL not configured, skipping AI analysis")
        return None
    
    # Prepare the payload
    payload = {
        "ticket_id": str(ticket_id),
        "title": title,
        "description": description
    }
    
    try:
        logger.info(f"Sending ticket #{ticket_id} to n8n webhook: {webhook_url}")
        
        # Send POST request to n8n webhook
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=30,  # 30 second timeout
            headers={'Content-Type': 'application/json'}
        )
        
        # Check if request was successful
        if response.status_code == 200:
            # Log raw response for debugging
            logger.info(f"Raw response from n8n for ticket #{ticket_id}: {response.text[:500] if response.text else 'EMPTY'}")
            
            # Parse the response
            try:
                response_data = response.json()
                logger.info(f"Parsed JSON response: {response_data}")
                
                # Extract the AI response text
                # Handle different possible response formats
                ai_response = None
                if isinstance(response_data, dict):
                    # Try standard fields first
                    ai_response = response_data.get('response') or response_data.get('analysis') or response_data.get('message')
                    
                    # If not found, try OpenAI chat completion format
                    if not ai_response and 'choices' in response_data:
                        try:
                            choices = response_data.get('choices', [])
                            if choices and len(choices) > 0:
                                message = choices[0].get('message', {})
                                content = message.get('content')
                                # Content might be a dict with 'response' field
                                if isinstance(content, dict):
                                    ai_response = content.get('response') or content.get('analysis') or content.get('message')
                                elif isinstance(content, str):
                                    ai_response = content
                        except (IndexError, KeyError, TypeError) as e:
                            logger.warning(f"Error extracting from OpenAI format: {e}")
                            
                elif isinstance(response_data, str):
                    ai_response = response_data
                else:
                    ai_response = str(response_data)
                
                if ai_response:
                    logger.info(f"Successfully received AI analysis for ticket #{ticket_id}")
                    return ai_response
                else:
                    logger.warning(f"n8n webhook returned response but no AI text found. Response keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'N/A'}")
                    return None
                    
            except ValueError as e:
                # Response is not JSON, treat as plain text
                logger.info(f"Response is not JSON, treating as plain text")
                ai_response = response.text
                if ai_response:
                    logger.info(f"Received plain text AI analysis for ticket #{ticket_id}")
                    return ai_response
                else:
                    logger.warning(f"n8n webhook returned empty text response for ticket #{ticket_id}")
                    return None
        else:
            logger.error(f"n8n webhook returned status {response.status_code} for ticket #{ticket_id}: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        logger.error(f"Timeout while sending ticket #{ticket_id} to n8n webhook")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending ticket #{ticket_id} to n8n webhook: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in n8n webhook integration for ticket #{ticket_id}: {str(e)}")
        return None
