import os
import requests
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

def format_ai_analysis(analysis_data: Dict[str, Any]) -> str:
    """
    Format AI analysis data into HTML for display in comments
    
    Args:
        analysis_data: Dictionary containing AI analysis fields
        
    Returns:
        Formatted HTML string
    """
    html_parts = []
    
    # Add summary if available
    if analysis_data.get('summary'):
        html_parts.append(f"<p><strong>📋 Summary:</strong><br>{analysis_data['summary']}</p>")
    
    # Add possible causes if available
    if analysis_data.get('possible_causes'):
        causes = analysis_data['possible_causes']
        if isinstance(causes, list):
            html_parts.append("<p><strong>🔍 Possible Causes:</strong></p><ul>")
            for cause in causes:
                html_parts.append(f"<li>{cause}</li>")
            html_parts.append("</ul>")
    
    # Add suggested solutions if available
    if analysis_data.get('suggested_solutions'):
        solutions = analysis_data['suggested_solutions']
        if isinstance(solutions, list):
            html_parts.append("<p><strong>💡 Suggested Solutions:</strong></p><ol>")
            for solution in solutions:
                html_parts.append(f"<li>{solution}</li>")
            html_parts.append("</ol>")
    
    # Add references if available
    if analysis_data.get('references'):
        references = analysis_data['references']
        if isinstance(references, list) and references:
            html_parts.append("<p><strong>📚 References:</strong></p><ul>")
            for ref in references:
                html_parts.append(f"<li><a href='{ref}' target='_blank'>{ref}</a></li>")
            html_parts.append("</ul>")
    
    # Add confidence level if available
    if analysis_data.get('confidence'):
        html_parts.append(f"<p><strong>📊 Confidence Level:</strong> {analysis_data['confidence']}</p>")
    
    # Add response/main analysis if available
    if analysis_data.get('response'):
        html_parts.append(f"<p><strong>💬 Analysis:</strong><br>{analysis_data['response']}</p>")
    
    return ''.join(html_parts)


def send_ticket_to_n8n(ticket_id: int, title: str, description: str) -> Optional[str]:
    """
    Send ticket information to n8n webhook for AI analysis
    
    Args:
        ticket_id: The ticket ID
        title: The ticket title
        description: The ticket description
        
    Returns:
        The formatted AI analysis HTML, or None if the request fails
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
                
                # Extract the AI analysis data
                # Handle different possible response formats
                analysis_data = None
                
                if isinstance(response_data, dict):
                    # Check if it's OpenAI chat completion format
                    if 'choices' in response_data:
                        try:
                            choices = response_data.get('choices', [])
                            if choices and len(choices) > 0:
                                message = choices[0].get('message', {})
                                content = message.get('content')
                                # Content should be a dict with structured fields
                                if isinstance(content, dict):
                                    analysis_data = content
                                elif isinstance(content, str):
                                    # If content is a string, wrap it in a dict
                                    analysis_data = {'response': content}
                        except (IndexError, KeyError, TypeError) as e:
                            logger.warning(f"Error extracting from OpenAI format: {e}")
                    else:
                        # Standard format - response_data is already the analysis
                        analysis_data = response_data
                            
                elif isinstance(response_data, str):
                    # Plain text response
                    analysis_data = {'response': response_data}
                
                # Format and return the analysis
                if analysis_data:
                    # Check if we have any meaningful data
                    has_data = any([
                        analysis_data.get('summary'),
                        analysis_data.get('possible_causes'),
                        analysis_data.get('suggested_solutions'),
                        analysis_data.get('references'),
                        analysis_data.get('confidence'),
                        analysis_data.get('response'),
                        analysis_data.get('analysis'),
                        analysis_data.get('message')
                    ])
                    
                    if has_data:
                        formatted_analysis = format_ai_analysis(analysis_data)
                        logger.info(f"Successfully received and formatted AI analysis for ticket #{ticket_id}")
                        return formatted_analysis
                    else:
                        logger.warning(f"n8n webhook returned response but no recognizable AI data. Keys: {list(analysis_data.keys())}")
                        return None
                else:
                    logger.warning(f"n8n webhook returned response but could not extract analysis data")
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
