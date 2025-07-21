import os
import json
import logging
import boto3
import psycopg2
from psycopg2.extras import RealDictCursor
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Database connection parameters
DB_HOST = os.environ.get("DB_HOST")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_PORT = os.environ.get("DB_PORT", "5432")

# Email configuration
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "notifications@loaneligibility.example.com")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Initialize AWS SES client
ses_client = boto3.client('ses', region_name=AWS_REGION)

def get_db_connection():
    """Create a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise e

def format_currency(amount):
    """Format a number as USD currency."""
    if amount is None:
        return "N/A"
    return "${:,.0f}".format(float(amount))

def send_email(recipient, subject, html_body):
    """
    Send an email using AWS SES.
    
    Args:
        recipient: Email address of the recipient
        subject: Email subject line
        html_body: HTML content of the email
        
    Returns:
        Dict with status and message
    """
    # Create a multipart message
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient
    
    # Add HTML body
    msg.attach(MIMEText(html_body, 'html'))
    
    try:
        # Send the email
        response = ses_client.send_raw_email(
            Source=SENDER_EMAIL,
            Destinations=[recipient],
            RawMessage={'Data': msg.as_string()}
        )
        
        logger.info(f"Email sent! Message ID: {response['MessageId']}")
        return {
            "status": "success",
            "message_id": response['MessageId']
        }
        
    except ClientError as e:
        logger.error(f"Error sending email: {e.response['Error']['Message']}")
        return {
            "status": "error",
            "message": e.response['Error']['Message']
        }

def generate_email_content(user, matches):
    """
    Generate personalized email content based on user data and loan matches.
    
    Args:
        user: Dict containing user information
        matches: List of dicts containing loan product matches
        
    Returns:
        Tuple of (subject, html_body)
    """
    # Generate the email subject
    subject = f"Good news! We've found {len(matches)} loan {len(matches) == 1 and 'option' or 'options'} for you"
    
    # Generate the email body
    html_body = f"""
<!DOCTYPE html>
<html>
<head>
  <style>
    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
    .header {{ background-color: #3498db; color: white; padding: 20px; text-align: center; }}
    .content {{ padding: 20px; }}
    .loan-item {{ border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; border-radius: 5px; }}
    .loan-name {{ color: #3498db; font-size: 18px; font-weight: bold; }}
    .loan-provider {{ color: #777; }}
    .loan-details {{ margin-top: 10px; }}
    .loan-match {{ background-color: #f8f9fa; padding: 5px 10px; border-radius: 15px; font-size: 14px; }}
    .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #777; }}
    .button {{ display: inline-block; background-color: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Loan Eligibility Results</h1>
    </div>
    <div class="content">
      <p>Dear {user['email'].split('@')[0]},</p>
      <p>We're pleased to inform you that based on your financial profile, you may be eligible for the following loan products:</p>
"""

    # Add each loan product to the email
    for match in matches:
        match_score = round(float(match['match_score']))
        html_body += f"""
      <div class="loan-item">
        <div class="loan-name">{match['product_name']}</div>
        <div class="loan-provider">from {match['provider_name']}</div>
        <div class="loan-details">
          <p><strong>Interest Rate:</strong> {match['interest_rate']}%</p>
          <p><strong>Loan Amount:</strong> {format_currency(match['min_loan_amount'])} - {format_currency(match['max_loan_amount'])}</p>
          <p><strong>Term:</strong> {match['loan_term_months']} months</p>
          <p><span class="loan-match">Match Score: {match_score}%</span></p>
        </div>
      </div>
"""

    # Complete the email
    html_body += f"""
      <p>These matches are based on the information you provided. To proceed with any of these options, please visit the lender's website or contact them directly.</p>
      <p>If you have any questions about these recommendations, feel free to contact our support team.</p>
      <p>Best regards,<br>Loan Eligibility Engine Team</p>
    </div>
    <div class="footer">
      <p>This is an automated email. Please do not reply directly to this message.</p>
      <p>© {2023} Loan Eligibility Engine</p>
    </div>
  </div>
</body>
</html>
"""
    
    return subject, html_body

def lambda_handler(event, context):
    """
    AWS Lambda handler for sending loan match notifications via email.
    
    This function:
    1. Receives user_id from the event
    2. Retrieves user data and their loan matches from the database
    3. Generates a personalized email
    4. Sends the email using AWS SES
    5. Updates the notification status in the database
    
    Args:
        event: Dict containing user_id
        context: AWS Lambda context
        
    Returns:
        Dict with status and results
    """
    try:
        # Extract parameters from the event
        body = json.loads(event.get("body", "{}"))
        user_id = body.get("user_id")
        batch_id = body.get("batch_id")
        
        if not (user_id or batch_id):
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "status": "error",
                    "message": "Missing required parameters: either user_id or batch_id"
                })
            }
        
        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            if user_id:
                # Get user data for a specific user
                cursor.execute("""
                    SELECT user_id, email, monthly_income, credit_score
                    FROM users
                    WHERE user_id = %s
                """, (user_id,))
                users = [cursor.fetchone()]
                
                if not users[0]:
                    return {
                        "statusCode": 404,
                        "body": json.dumps({
                            "status": "error",
                            "message": f"User with ID {user_id} not found"
                        })
                    }
            else:
                # Get all users in a batch
                cursor.execute("""
                    SELECT DISTINCT u.user_id, u.email, u.monthly_income, u.credit_score
                    FROM users u
                    JOIN matches m ON u.user_id = m.user_id
                    WHERE u.batch_id = %s
                    AND m.notified = FALSE
                """, (batch_id,))
                users = cursor.fetchall()
                
                if not users:
                    return {
                        "statusCode": 200,
                        "body": json.dumps({
                            "status": "success",
                            "message": f"No users found with unnotified matches in batch {batch_id}"
                        })
                    }
            
            results = []
            
            # Process each user
            for user in users:
                # Get user's matches
                cursor.execute("""
                    SELECT m.match_id, m.user_id, m.product_id, m.match_score,
                           lp.provider_name, lp.product_name, lp.interest_rate,
                           lp.min_loan_amount, lp.max_loan_amount, lp.loan_term_months
                    FROM matches m
                    JOIN loan_products lp ON m.product_id = lp.product_id
                    WHERE m.user_id = %s
                    AND m.notified = FALSE
                    ORDER BY m.match_score DESC
                """, (user['user_id'],))
                matches = cursor.fetchall()
                
                if not matches:
                    results.append({
                        "user_id": user['user_id'],
                        "email": user['email'],
                        "status": "skipped",
                        "reason": "No matches found"
                    })
                    continue
                
                # Generate email content
                subject, html_body = generate_email_content(user, matches)
                
                # Send email
                email_result = send_email(user['email'], subject, html_body)
                
                if email_result['status'] == 'success':
                    # Update matches as notified
                    match_ids = [match['match_id'] for match in matches]
                    cursor.execute("""
                        UPDATE matches
                        SET notified = TRUE
                        WHERE match_id = ANY(%s)
                    """, (match_ids,))
                    
                    # Log notification
                    cursor.execute("""
                        INSERT INTO notifications (user_id, email_subject, email_body, status)
                        VALUES (%s, %s, %s, 'sent')
                    """, (user['user_id'], subject, html_body))
                    
                    conn.commit()
                    
                    results.append({
                        "user_id": user['user_id'],
                        "email": user['email'],
                        "status": "sent",
                        "matches_count": len(matches),
                        "message_id": email_result.get('message_id')
                    })
                else:
                    results.append({
                        "user_id": user['user_id'],
                        "email": user['email'],
                        "status": "error",
                        "reason": email_result.get('message')
                    })
            
            # Return the results
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "status": "success",
                    "users_processed": len(users),
                    "results": results
                })
            }
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {str(e)}")
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "status": "error",
                    "message": f"Database error: {str(e)}"
                })
            }
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Lambda error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "error",
                "message": f"Lambda error: {str(e)}"
            })
        }
