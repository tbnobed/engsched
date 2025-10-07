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
            # Parse the response
            try:
                response_data = response.json()
                
                # Extract the AI response text
                # Handle different possible response formats
                if isinstance(response_data, dict):
                    ai_response = response_data.get('response') or response_data.get('analysis') or response_data.get('message')
                elif isinstance(response_data, str):
                    ai_response = response_data
                else:
                    ai_response = str(response_data)
                
                if ai_response:
                    logger.info(f"Successfully received AI analysis for ticket #{ticket_id}")
                    return ai_response
                else:
                    logger.warning(f"n8n webhook returned empty response for ticket #{ticket_id}")
                    return None
                    
            except ValueError as e:
                # Response is not JSON, treat as plain text
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
