#!/usr/bin/env python3
"""
End-to-End Test Script for Loan Eligibility Engine

This script tests the entire loan eligibility pipeline:
1. Generates sample user data and loan products
2. Uploads user data to S3
3. Monitors the database for processing
4. Validates the results

Usage:
    python test_system.py --users 10 --products 5
"""

import os
import time
import boto3
import argparse
import psycopg2
import requests
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from generate_sample_data import generate_user_data, generate_loan_products, insert_loan_products

# Load environment variables
load_dotenv()

# AWS configuration
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
S3_BUCKET = os.environ.get("S3_BUCKET")

# Database connection parameters
DB_HOST = os.environ.get("DB_HOST")
DB_NAME = os.environ.get("DB_NAME", "loaneligibility")
DB_USER = os.environ.get("DB_USER", "admin")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_PORT = os.environ.get("DB_PORT", "5432")

# n8n webhook URLs
N8N_MATCHING_WEBHOOK = os.environ.get("N8N_MATCHING_WEBHOOK", "http://localhost:5678/webhook/loan-matching")
N8N_NOTIFICATION_WEBHOOK = os.environ.get("N8N_NOTIFICATION_WEBHOOK", "http://localhost:5678/webhook/loan-notification")

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
        print(f"Database connection error: {str(e)}")
        raise e

def upload_to_s3(file_path, bucket_name):
    """
    Upload a file to S3.
    
    Args:
        file_path: Path to the file to upload
        bucket_name: Name of the S3 bucket
        
    Returns:
        S3 object URL
    """
    if not bucket_name:
        print("S3_BUCKET environment variable not set. Skipping S3 upload.")
        return None
    
    try:
        s3_client = boto3.client('s3', region_name=AWS_REGION)
        file_name = os.path.basename(file_path)
        
        print(f"Uploading {file_name} to S3 bucket {bucket_name}...")
        s3_client.upload_file(file_path, bucket_name, file_name)
        
        object_url = f"https://{bucket_name}.s3.amazonaws.com/{file_name}"
        print(f"File uploaded successfully: {object_url}")
        return object_url
    
    except Exception as e:
        print(f"Error uploading to S3: {str(e)}")
        return None

def trigger_webhook(webhook_url, payload):
    """
    Trigger an n8n webhook.
    
    Args:
        webhook_url: URL of the webhook
        payload: JSON payload to send
        
    Returns:
        Response from the webhook
    """
    try:
        print(f"Triggering webhook: {webhook_url}")
        response = requests.post(webhook_url, json=payload)
        print(f"Webhook response: {response.status_code} - {response.text}")
        return response
    
    except Exception as e:
        print(f"Error triggering webhook: {str(e)}")
        return None

def monitor_database(batch_id, timeout=300):
    """
    Monitor the database for processing of a specific batch.
    
    Args:
        batch_id: Batch ID to monitor
        timeout: Maximum time to wait in seconds
        
    Returns:
        Dictionary with monitoring results
    """
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    start_time = time.time()
    end_time = start_time + timeout
    
    results = {
        "users_processed": 0,
        "matches_created": 0,
        "notifications_sent": 0,
        "processing_complete": False
    }
    
    try:
        print(f"Monitoring database for batch {batch_id}...")
        
        while time.time() < end_time:
            # Check users processed
            cursor.execute("""
                SELECT COUNT(*) as count FROM users WHERE batch_id = %s
            """, (batch_id,))
            users_count = cursor.fetchone()["count"]
            
            # Check matches created
            cursor.execute("""
                SELECT COUNT(*) as count FROM matches m
                JOIN users u ON m.user_id = u.user_id
                WHERE u.batch_id = %s
            """, (batch_id,))
            matches_count = cursor.fetchone()["count"]
            
            # Check notifications sent
            cursor.execute("""
                SELECT COUNT(*) as count FROM notifications n
                JOIN users u ON n.user_id = u.user_id
                WHERE u.batch_id = %s
            """, (batch_id,))
            notifications_count = cursor.fetchone()["count"]
            
            # Update results
            results["users_processed"] = users_count
            results["matches_created"] = matches_count
            results["notifications_sent"] = notifications_count
            
            # Print progress
            print(f"Progress: {users_count} users, {matches_count} matches, {notifications_count} notifications")
            
            # Check if processing is complete
            if users_count > 0 and matches_count > 0 and notifications_count > 0:
                results["processing_complete"] = True
                break
            
            # Wait before checking again
            time.sleep(10)
        
        return results
    
    except Exception as e:
        print(f"Error monitoring database: {str(e)}")
        return results
    
    finally:
        cursor.close()
        conn.close()

def main():
    """Main function to test the system."""
    parser = argparse.ArgumentParser(description='Test the Loan Eligibility Engine')
    parser.add_argument('--users', type=int, default=10, help='Number of users to generate')
    parser.add_argument('--products', type=int, default=5, help='Number of loan products to generate')
    parser.add_argument('--output-dir', type=str, default='./sample_data', help='Output directory for sample data')
    parser.add_argument('--skip-s3', action='store_true', help='Skip S3 upload')
    parser.add_argument('--skip-webhook', action='store_true', help='Skip webhook triggers')
    parser.add_argument('--timeout', type=int, default=300, help='Monitoring timeout in seconds')
    
    args = parser.parse_args()
    
    # Generate user data CSV
    user_csv_path = generate_user_data(args.users, args.output_dir)
    
    # Extract batch ID from the CSV filename
    batch_id = os.path.basename(user_csv_path).split('_')[2].split('.')[0]
    
    # Generate and insert loan products
    loan_products = generate_loan_products(args.products)
    insert_loan_products(loan_products)
    
    # Upload user data to S3
    if not args.skip_s3 and S3_BUCKET:
        s3_url = upload_to_s3(user_csv_path, S3_BUCKET)
        
        if not s3_url:
            print("S3 upload failed. Exiting.")
            return
    else:
        print("Skipping S3 upload.")
    
    # Trigger webhooks manually if requested
    if not args.skip_webhook:
        # Trigger matching webhook
        matching_payload = {"batch_id": batch_id}
        trigger_webhook(N8N_MATCHING_WEBHOOK, matching_payload)
        
        # Wait a bit for matching to complete
        time.sleep(30)
        
        # Trigger notification webhook
        notification_payload = {"batch_id": batch_id}
        trigger_webhook(N8N_NOTIFICATION_WEBHOOK, notification_payload)
    
    # Monitor the database
    results = monitor_database(batch_id, args.timeout)
    
    # Print final results
    print("\nTest Results:")
    print(f"Users Processed: {results['users_processed']}")
    print(f"Matches Created: {results['matches_created']}")
    print(f"Notifications Sent: {results['notifications_sent']}")
    print(f"Processing Complete: {results['processing_complete']}")
    
    if results['processing_complete']:
        print("\nTest completed successfully!")
    else:
        print("\nTest did not complete within the timeout period.")
        print("You may need to check the system logs for errors.")

if __name__ == "__main__":
    main()
