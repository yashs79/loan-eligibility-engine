#!/usr/bin/env python3
"""
Sample Data Generator for Loan Eligibility Engine

This script generates:
1. Sample user data CSV files
2. Sample loan product data
3. Inserts sample loan products directly into the database

Usage:
    python generate_sample_data.py --users 100 --products 20 --output-dir ./sample_data
"""

import os
import csv
import json
import random
import argparse
import psycopg2
from datetime import datetime
from faker import Faker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Faker
fake = Faker()

# Database connection parameters
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME", "loaneligibility")
DB_USER = os.environ.get("DB_USER", "admin")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "password")
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
        print(f"Database connection error: {str(e)}")
        raise e

def generate_user_data(count, output_dir):
    """
    Generate sample user data and save to CSV.
    
    Args:
        count: Number of users to generate
        output_dir: Directory to save the CSV file
    
    Returns:
        Path to the generated CSV file
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate a timestamp for the batch ID
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    batch_id = f"BATCH_{timestamp}"
    
    # Define the CSV file path
    csv_path = os.path.join(output_dir, f"user_data_{timestamp}.csv")
    
    # Define the CSV headers
    headers = [
        "email", 
        "full_name", 
        "age", 
        "monthly_income", 
        "credit_score",
        "employment_status",
        "debt_to_income_ratio",
        "existing_loans"
    ]
    
    # Generate user data
    users = []
    for _ in range(count):
        # Generate random user data
        age = random.randint(21, 75)
        monthly_income = random.randint(2000, 15000)
        credit_score = random.randint(500, 850)
        employment_status = random.choice(["employed", "self-employed", "unemployed", "retired"])
        debt_to_income_ratio = round(random.uniform(0.1, 0.6), 2)
        existing_loans = random.randint(0, 3)
        
        user = {
            "email": fake.email(),
            "full_name": fake.name(),
            "age": age,
            "monthly_income": monthly_income,
            "credit_score": credit_score,
            "employment_status": employment_status,
            "debt_to_income_ratio": debt_to_income_ratio,
            "existing_loans": existing_loans
        }
        users.append(user)
    
    # Write user data to CSV
    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        writer.writerows(users)
    
    print(f"Generated {count} users in {csv_path}")
    return csv_path

def generate_loan_products(count):
    """
    Generate sample loan product data.
    
    Args:
        count: Number of loan products to generate
    
    Returns:
        List of loan product dictionaries
    """
    # Define bank names
    banks = [
        "First National Bank",
        "City Credit Union",
        "Global Financial",
        "Heritage Bank",
        "Prosperity Lending",
        "Coastal Credit",
        "Mountain State Bank",
        "Evergreen Financial",
        "Liberty Loans",
        "Sunrise Banking"
    ]
    
    # Define loan product types
    product_types = [
        "Personal Loan",
        "Home Improvement Loan",
        "Debt Consolidation Loan",
        "Auto Loan",
        "Education Loan",
        "Small Business Loan"
    ]
    
    # Generate loan products
    products = []
    for _ in range(count):
        # Generate random loan product data
        provider_name = random.choice(banks)
        product_type = random.choice(product_types)
        product_name = f"{provider_name} {product_type}"
        
        interest_rate = round(random.uniform(3.5, 18.5), 2)
        min_loan_amount = random.choice([1000, 2000, 2500, 5000, 10000])
        max_loan_amount = min_loan_amount * random.randint(5, 20)
        loan_term_months = random.choice([12, 24, 36, 48, 60, 72, 84])
        
        min_credit_score = random.randint(580, 720)
        min_monthly_income = random.randint(1500, 5000)
        max_debt_to_income = round(random.uniform(0.3, 0.5), 2)
        
        product = {
            "provider_name": provider_name,
            "product_name": product_name,
            "interest_rate": interest_rate,
            "min_loan_amount": min_loan_amount,
            "max_loan_amount": max_loan_amount,
            "loan_term_months": loan_term_months,
            "min_credit_score": min_credit_score,
            "min_monthly_income": min_monthly_income,
            "max_debt_to_income": max_debt_to_income,
            "product_url": f"https://example.com/{provider_name.lower().replace(' ', '-')}/loans/{product_type.lower().replace(' ', '-')}"
        }
        products.append(product)
    
    return products

def insert_loan_products(products):
    """
    Insert loan products into the database.
    
    Args:
        products: List of loan product dictionaries
    
    Returns:
        Number of products inserted
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Insert each product
        for product in products:
            cursor.execute("""
                INSERT INTO loan_products (
                    provider_name, product_name, interest_rate,
                    min_loan_amount, max_loan_amount, loan_term_months,
                    min_credit_score, min_monthly_income, max_debt_to_income,
                    product_url
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (provider_name, product_name) DO NOTHING
            """, (
                product["provider_name"],
                product["product_name"],
                product["interest_rate"],
                product["min_loan_amount"],
                product["max_loan_amount"],
                product["loan_term_months"],
                product["min_credit_score"],
                product["min_monthly_income"],
                product["max_debt_to_income"],
                product["product_url"]
            ))
        
        conn.commit()
        print(f"Inserted {len(products)} loan products into the database")
        return len(products)
    
    except Exception as e:
        conn.rollback()
        print(f"Error inserting loan products: {str(e)}")
        raise e
    
    finally:
        cursor.close()
        conn.close()

def save_loan_products_json(products, output_dir):
    """
    Save loan products to a JSON file.
    
    Args:
        products: List of loan product dictionaries
        output_dir: Directory to save the JSON file
    
    Returns:
        Path to the generated JSON file
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate a timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Define the JSON file path
    json_path = os.path.join(output_dir, f"loan_products_{timestamp}.json")
    
    # Write products to JSON
    with open(json_path, 'w') as jsonfile:
        json.dump(products, jsonfile, indent=2)
    
    print(f"Saved {len(products)} loan products to {json_path}")
    return json_path

def main():
    """Main function to generate sample data."""
    parser = argparse.ArgumentParser(description='Generate sample data for Loan Eligibility Engine')
    parser.add_argument('--users', type=int, default=50, help='Number of users to generate')
    parser.add_argument('--products', type=int, default=10, help='Number of loan products to generate')
    parser.add_argument('--output-dir', type=str, default='./sample_data', help='Output directory for sample data')
    parser.add_argument('--db-insert', action='store_true', help='Insert loan products into the database')
    
    args = parser.parse_args()
    
    # Generate user data CSV
    user_csv_path = generate_user_data(args.users, args.output_dir)
    
    # Generate loan products
    loan_products = generate_loan_products(args.products)
    
    # Save loan products to JSON
    json_path = save_loan_products_json(loan_products, args.output_dir)
    
    # Insert loan products into database if requested
    if args.db_insert:
        insert_loan_products(loan_products)
    
    print("\nSample Data Generation Complete!")
    print(f"User CSV: {user_csv_path}")
    print(f"Loan Products JSON: {json_path}")
    print(f"Generated {args.users} users and {args.products} loan products")
    
    # Print instructions for testing
    print("\nTo test the system:")
    print("1. Upload the user CSV file to the S3 bucket")
    print("2. If you didn't use --db-insert, import the loan products JSON into the database")
    print("3. Monitor the n8n workflows for processing")

if __name__ == "__main__":
    main()
