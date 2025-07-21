import os
import json
import logging
import boto3
import psycopg2
from psycopg2.extras import RealDictCursor
from ai_eligibility_checker import AIEligibilityChecker

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize the AI checker
ai_checker = AIEligibilityChecker(api_type=os.environ.get("AI_API_TYPE", "openai"))

# Database connection parameters
DB_HOST = os.environ.get("DB_HOST")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_PORT = os.environ.get("DB_PORT", "5432")

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

def lambda_handler(event, context):
    """
    AWS Lambda handler for AI-based loan eligibility checking.
    
    This function:
    1. Receives user_id and product_id from the event
    2. Retrieves user and loan product data from the database
    3. Uses AI to determine eligibility
    4. Updates the match record with AI evaluation results
    
    Args:
        event: Dict containing user_id and product_id
        context: AWS Lambda context
        
    Returns:
        Dict with status and results
    """
    try:
        # Extract parameters from the event
        body = json.loads(event.get("body", "{}"))
        user_id = body.get("user_id")
        product_id = body.get("product_id")
        
        if not user_id or not product_id:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "status": "error",
                    "message": "Missing required parameters: user_id and product_id"
                })
            }
        
        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Get user data
            cursor.execute("""
                SELECT user_id, email, monthly_income, credit_score, 
                       employment_status, age, debt_to_income_ratio, existing_loans
                FROM users
                WHERE user_id = %s
            """, (user_id,))
            user_data = cursor.fetchone()
            
            if not user_data:
                return {
                    "statusCode": 404,
                    "body": json.dumps({
                        "status": "error",
                        "message": f"User with ID {user_id} not found"
                    })
                }
            
            # Get loan product data
            cursor.execute("""
                SELECT product_id, provider_name, product_name, interest_rate,
                       min_loan_amount, max_loan_amount, loan_term_months,
                       min_credit_score, min_monthly_income, max_debt_to_income
                FROM loan_products
                WHERE product_id = %s
            """, (product_id,))
            loan_product = cursor.fetchone()
            
            if not loan_product:
                return {
                    "statusCode": 404,
                    "body": json.dumps({
                        "status": "error",
                        "message": f"Loan product with ID {product_id} not found"
                    })
                }
            
            # Check eligibility using AI
            eligible, confidence, reason = ai_checker.check_eligibility(user_data, loan_product)
            
            # Calculate match score (0-100)
            match_score = confidence if eligible else confidence * 0.5
            
            # Update the match record in the database
            cursor.execute("""
                UPDATE matches
                SET ai_eligible = %s,
                    ai_confidence = %s,
                    ai_reason = %s,
                    match_score = %s,
                    ai_evaluated_at = NOW()
                WHERE user_id = %s AND product_id = %s
                RETURNING match_id
            """, (eligible, confidence, reason, match_score, user_id, product_id))
            
            match = cursor.fetchone()
            conn.commit()
            
            if not match:
                # If no match record exists, create one
                cursor.execute("""
                    INSERT INTO matches
                    (user_id, product_id, ai_eligible, ai_confidence, ai_reason, match_score, ai_evaluated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    RETURNING match_id
                """, (user_id, product_id, eligible, confidence, reason, match_score))
                match = cursor.fetchone()
                conn.commit()
            
            # Return the results
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "status": "success",
                    "match_id": match["match_id"],
                    "user_id": user_id,
                    "product_id": product_id,
                    "eligible": eligible,
                    "confidence": confidence,
                    "reason": reason,
                    "match_score": match_score
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
