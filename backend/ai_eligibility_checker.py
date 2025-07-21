import os
import json
import logging
import requests
from typing import Dict, Any, Optional, Tuple

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class AIEligibilityChecker:
    """
    A class to handle AI-based eligibility checks for loan applications.
    Supports both OpenAI GPT and Google Gemini APIs.
    """
    
    def __init__(self, api_type: str = "openai"):
        """
        Initialize the AI eligibility checker.
        
        Args:
            api_type: The type of AI API to use ('openai' or 'gemini')
        """
        self.api_type = api_type.lower()
        
        # Load API keys from environment variables
        if self.api_type == "openai":
            self.api_key = os.environ.get("OPENAI_API_KEY")
            if not self.api_key:
                logger.warning("OPENAI_API_KEY not found in environment variables")
        elif self.api_type == "gemini":
            self.api_key = os.environ.get("GEMINI_API_KEY")
            if not self.api_key:
                logger.warning("GEMINI_API_KEY not found in environment variables")
        else:
            raise ValueError(f"Unsupported API type: {api_type}. Use 'openai' or 'gemini'.")
    
    def check_eligibility(self, user_data: Dict[str, Any], loan_product: Dict[str, Any]) -> Tuple[bool, float, str]:
        """
        Check if a user is eligible for a loan product using AI.
        
        Args:
            user_data: Dictionary containing user financial information
            loan_product: Dictionary containing loan product details
            
        Returns:
            Tuple containing (is_eligible, confidence_score, reason)
        """
        if self.api_type == "openai":
            return self._check_with_openai(user_data, loan_product)
        else:
            return self._check_with_gemini(user_data, loan_product)
    
    def _check_with_openai(self, user_data: Dict[str, Any], loan_product: Dict[str, Any]) -> Tuple[bool, float, str]:
        """
        Check eligibility using OpenAI's GPT API.
        """
        if not self.api_key:
            logger.error("OpenAI API key not configured")
            return False, 0.0, "API key not configured"
        
        # Prepare the prompt
        prompt = self._create_prompt(user_data, loan_product)
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a loan eligibility expert. Your task is to evaluate if a user with specific financial characteristics would be eligible for a loan product, even if they are slightly below the standard requirements. Consider factors like employment stability, debt-to-income ratio, and overall financial health. Respond with a JSON object containing 'eligible' (boolean), 'confidence' (number between 0-100), and 'reason' (string)."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.2
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            response.raise_for_status()
            response_data = response.json()
            
            # Extract the response content
            content = response_data["choices"][0]["message"]["content"]
            
            # Parse the JSON response
            try:
                result = json.loads(content)
                eligible = result.get("eligible", False)
                confidence = float(result.get("confidence", 0))
                reason = result.get("reason", "No reason provided")
                
                return eligible, confidence, reason
                
            except json.JSONDecodeError:
                # If not valid JSON, try to extract using regex
                import re
                
                eligible_match = re.search(r'"eligible"\s*:\s*(true|false)', content, re.IGNORECASE)
                eligible = eligible_match and eligible_match.group(1).lower() == 'true'
                
                confidence_match = re.search(r'"confidence"\s*:\s*(\d+)', content, re.IGNORECASE)
                confidence = float(confidence_match.group(1)) if confidence_match else 0
                
                reason_match = re.search(r'"reason"\s*:\s*"([^"]+)"', content, re.IGNORECASE)
                reason = reason_match.group(1) if reason_match else "No reason provided"
                
                return eligible, confidence, reason
                
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            return False, 0.0, f"API error: {str(e)}"
    
    def _check_with_gemini(self, user_data: Dict[str, Any], loan_product: Dict[str, Any]) -> Tuple[bool, float, str]:
        """
        Check eligibility using Google's Gemini API.
        """
        if not self.api_key:
            logger.error("Gemini API key not configured")
            return False, 0.0, "API key not configured"
        
        # Prepare the prompt
        prompt = self._create_prompt(user_data, loan_product)
        
        try:
            headers = {
                "Content-Type": "application/json"
            }
            
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": "You are a loan eligibility expert. Your task is to evaluate if a user with specific financial characteristics would be eligible for a loan product, even if they are slightly below the standard requirements. Consider factors like employment stability, debt-to-income ratio, and overall financial health. Respond with a JSON object containing 'eligible' (boolean), 'confidence' (number between 0-100), and 'reason' (string)."
                            }
                        ]
                    },
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2
                }
            }
            
            # Gemini API endpoint
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={self.api_key}"
            
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            response_data = response.json()
            
            # Extract the response content
            content = response_data["candidates"][0]["content"]["parts"][0]["text"]
            
            # Parse the JSON response
            try:
                result = json.loads(content)
                eligible = result.get("eligible", False)
                confidence = float(result.get("confidence", 0))
                reason = result.get("reason", "No reason provided")
                
                return eligible, confidence, reason
                
            except json.JSONDecodeError:
                # If not valid JSON, try to extract using regex
                import re
                
                eligible_match = re.search(r'"eligible"\s*:\s*(true|false)', content, re.IGNORECASE)
                eligible = eligible_match and eligible_match.group(1).lower() == 'true'
                
                confidence_match = re.search(r'"confidence"\s*:\s*(\d+)', content, re.IGNORECASE)
                confidence = float(confidence_match.group(1)) if confidence_match else 0
                
                reason_match = re.search(r'"reason"\s*:\s*"([^"]+)"', content, re.IGNORECASE)
                reason = reason_match.group(1) if reason_match else "No reason provided"
                
                return eligible, confidence, reason
                
        except Exception as e:
            logger.error(f"Error calling Gemini API: {str(e)}")
            return False, 0.0, f"API error: {str(e)}"
    
    def _create_prompt(self, user_data: Dict[str, Any], loan_product: Dict[str, Any]) -> str:
        """
        Create a prompt for the AI model based on user data and loan product.
        
        Args:
            user_data: Dictionary containing user financial information
            loan_product: Dictionary containing loan product details
            
        Returns:
            String prompt for the AI model
        """
        prompt = f"""
Evaluate if this user is eligible for this loan product:

User Information:
Monthly Income: ${user_data.get('monthly_income', 'Not provided')}
Credit Score: {user_data.get('credit_score', 'Not provided')}
Employment Status: {user_data.get('employment_status', 'Not provided')}
Age: {user_data.get('age', 'Not provided')}
Debt-to-Income Ratio: {user_data.get('debt_to_income_ratio', 'Not provided')}
Existing Loans: {user_data.get('existing_loans', 'Not provided')}

Loan Product:
Provider: {loan_product.get('provider_name', 'Not provided')}
Product: {loan_product.get('product_name', 'Not provided')}
Interest Rate: {loan_product.get('interest_rate', 'Not provided')}%
Minimum Credit Score Requirement: {loan_product.get('min_credit_score', 'Not provided')}
Minimum Monthly Income: ${loan_product.get('min_monthly_income', 'Not provided')}
Maximum Debt-to-Income Ratio: {loan_product.get('max_debt_to_income', 'Not provided')}
Loan Amount Range: ${loan_product.get('min_loan_amount', 'Not provided')} - ${loan_product.get('max_loan_amount', 'Not provided')}
Loan Term: {loan_product.get('loan_term_months', 'Not provided')} months

The user is slightly below the standard requirements. Would you recommend approving them for this loan?
"""
        return prompt


# Example usage
if __name__ == "__main__":
    # Example user data
    user = {
        "user_id": 123,
        "email": "john.doe@example.com",
        "monthly_income": 4800,
        "credit_score": 680,
        "employment_status": "employed",
        "age": 35,
        "debt_to_income_ratio": 0.35,
        "existing_loans": 1
    }
    
    # Example loan product
    loan = {
        "product_id": 456,
        "provider_name": "Example Bank",
        "product_name": "Personal Loan Plus",
        "interest_rate": 7.5,
        "min_loan_amount": 5000,
        "max_loan_amount": 25000,
        "loan_term_months": 36,
        "min_credit_score": 700,
        "min_monthly_income": 5000,
        "max_debt_to_income": 0.4
    }
    
    # Initialize the checker with OpenAI
    checker = AIEligibilityChecker(api_type="openai")
    
    # Check eligibility
    eligible, confidence, reason = checker.check_eligibility(user, loan)
    
    print(f"Eligible: {eligible}")
    print(f"Confidence: {confidence}%")
    print(f"Reason: {reason}")
