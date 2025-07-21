# Loan Eligibility Engine - Architecture

## System Overview

The Loan Eligibility Engine is a cloud-native, event-driven system that:
1. Ingests user data via CSV uploads
2. Discovers loan products from public websites
3. Matches users to eligible loan products
4. Notifies users of their eligible loan products

## Core Components

### 1. User Data Ingestion Pipeline
- **Frontend UI**: Minimal web interface for CSV upload
- **S3 Bucket**: Temporary storage for uploaded CSV files
- **Lambda Function**: Triggered by S3 upload event, processes CSV data
- **RDS PostgreSQL**: Stores processed user data

### 2. n8n Automation Engine (Self-hosted via Docker)
- **Workflow A: Loan Product Discovery**
  - Scheduled web crawler that extracts loan product information
  - Stores structured data in PostgreSQL
  
- **Workflow B: User-Loan Matching**
  - Triggered by webhook after new user data is processed
  - Multi-stage matching pipeline:
    1. Fast SQL-based pre-filtering
    2. n8n rule-based filtering
    3. LLM-based qualitative assessment (for edge cases)
  - Stores matches in PostgreSQL
  
- **Workflow C: User Notification**
  - Triggered after matching process completes
  - Constructs personalized emails for users with matches
  - Sends emails via AWS SES

### 3. Database Schema
- **users**: Stores user information (user_id, email, monthly_income, credit_score, etc.)
- **loan_products**: Stores loan product information (product_id, name, interest_rate, eligibility criteria)
- **matches**: Links users to eligible loan products

### 4. Infrastructure
- **AWS Services**: S3, Lambda, RDS PostgreSQL, SES
- **Deployment**: Serverless Framework for AWS resources
- **n8n**: Self-hosted via Docker Compose

## Data Flow

1. User uploads CSV file through the frontend UI
2. CSV file is stored in S3 bucket
3. S3 event triggers Lambda function
4. Lambda processes CSV data and stores it in RDS
5. Lambda sends webhook to n8n to trigger matching workflow
6. n8n Workflow B matches users to loan products
7. n8n Workflow C sends notification emails to users

## Optimization Strategy

The multi-stage filtering pipeline optimizes the matching process:

1. **SQL Pre-filtering**: Fast database queries to eliminate obvious non-matches
   - Example: Filter out users with income below minimum requirements
   
2. **Rule-based Filtering in n8n**: Apply more complex business rules
   - Example: Calculate debt-to-income ratios and filter accordingly
   
3. **LLM-based Assessment**: Only for edge cases or nuanced criteria
   - Example: Evaluate employment stability or special circumstances
   
This approach minimizes API costs while maintaining high-quality matches.
