#!/bin/bash
# Loan Eligibility Engine Deployment Script
# This script deploys the Loan Eligibility Engine to AWS Free Tier

set -e  # Exit on error

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print colored message
print_message() {
  echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
  print_error "AWS CLI is not installed. Please install it first."
  exit 1
fi

# Check if Serverless Framework is installed
if ! command -v serverless &> /dev/null; then
  print_error "Serverless Framework is not installed. Please install it first."
  exit 1
fi

# Check if Docker is installed (for n8n)
if ! command -v docker &> /dev/null; then
  print_error "Docker is not installed. Please install it first."
  exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
  print_error "Docker Compose is not installed. Please install it first."
  exit 1
fi

# Check AWS credentials
print_message "Checking AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
  print_error "AWS credentials not configured. Please run 'aws configure' first."
  exit 1
fi

# Parse command line arguments
STAGE="dev"
REGION="us-east-1"
SKIP_N8N=false
SKIP_AWS=false

while [[ "$#" -gt 0 ]]; do
  case $1 in
    --stage) STAGE="$2"; shift ;;
    --region) REGION="$2"; shift ;;
    --skip-n8n) SKIP_N8N=true ;;
    --skip-aws) SKIP_AWS=true ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --stage STAGE    Deployment stage (default: dev)"
      echo "  --region REGION  AWS region (default: us-east-1)"
      echo "  --skip-n8n      Skip n8n deployment"
      echo "  --skip-aws      Skip AWS deployment"
      echo "  --help          Show this help message"
      exit 0
      ;;
    *) print_error "Unknown parameter: $1"; exit 1 ;;
  esac
  shift
done

# Create a secure DB password if not already in SSM
print_message "Checking for database password in SSM..."
if ! aws ssm get-parameter --name "/loan-eligibility/db-password" --region $REGION &> /dev/null; then
  print_message "Generating secure database password..."
  DB_PASSWORD=$(openssl rand -base64 16)
  aws ssm put-parameter \
    --name "/loan-eligibility/db-password" \
    --type "SecureString" \
    --value "$DB_PASSWORD" \
    --region $REGION \
    --overwrite
  print_message "Database password stored in SSM Parameter Store"
else
  print_message "Database password already exists in SSM Parameter Store"
fi

# Deploy AWS resources using Serverless Framework
if [ "$SKIP_AWS" = false ]; then
  print_message "Deploying AWS resources using Serverless Framework..."
  cd infrastructure
  
  # Deploy the serverless stack
  serverless deploy --stage $STAGE --region $REGION
  
  # Get the outputs from the deployment
  S3_BUCKET=$(aws cloudformation describe-stacks --stack-name loan-eligibility-engine-$STAGE --region $REGION --query "Stacks[0].Outputs[?OutputKey=='UserDataBucketName'].OutputValue" --output text)
  RDS_ENDPOINT=$(aws cloudformation describe-stacks --stack-name loan-eligibility-engine-$STAGE --region $REGION --query "Stacks[0].Outputs[?OutputKey=='RDSEndpoint'].OutputValue" --output text)
  RDS_PORT=$(aws cloudformation describe-stacks --stack-name loan-eligibility-engine-$STAGE --region $REGION --query "Stacks[0].Outputs[?OutputKey=='RDSPort'].OutputValue" --output text)
  
  print_message "AWS resources deployed successfully!"
  print_message "S3 Bucket: $S3_BUCKET"
  print_message "RDS Endpoint: $RDS_ENDPOINT:$RDS_PORT"
  
  # Initialize the database schema
  print_message "Initializing database schema..."
  DB_PASSWORD=$(aws ssm get-parameter --name "/loan-eligibility/db-password" --with-decryption --region $REGION --query "Parameter.Value" --output text)
  export PGPASSWORD=$DB_PASSWORD
  
  # Wait for RDS to be available
  print_message "Waiting for RDS instance to be available..."
  sleep 30
  
  # Apply the schema
  psql -h $RDS_ENDPOINT -p $RDS_PORT -U admin -d loaneligibility -f schema.sql
  
  print_message "Database schema initialized!"
  
  cd ..
fi

# Deploy n8n using Docker Compose
if [ "$SKIP_N8N" = false ]; then
  print_message "Deploying n8n using Docker Compose..."
  cd n8n
  
  # Create .env file if it doesn't exist
  if [ ! -f .env ]; then
    print_message "Creating .env file for n8n..."
    
    # Get the database password from SSM
    DB_PASSWORD=$(aws ssm get-parameter --name "/loan-eligibility/db-password" --with-decryption --region $REGION --query "Parameter.Value" --output text)
    
    # Create .env file
    cat > .env << EOL
# n8n Configuration
N8N_PORT=5678
N8N_PROTOCOL=http
N8N_HOST=localhost
N8N_ENCRYPTION_KEY=$(openssl rand -hex 24)
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=$(openssl rand -base64 12)

# Database Configuration
POSTGRES_USER=admin
POSTGRES_PASSWORD=$DB_PASSWORD
POSTGRES_DB=n8n
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# AWS Configuration
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=$REGION

# API Keys
OPENAI_API_KEY=
GEMINI_API_KEY=

# Email Configuration
SENDER_EMAIL=notifications@loaneligibility.example.com
EOL
    
    print_message ".env file created. Please fill in the missing values."
  fi
  
  # Start n8n
  docker-compose up -d
  
  print_message "n8n deployed successfully!"
  print_message "n8n is available at: http://localhost:5678"
  print_message "Username: admin"
  print_message "Password: Check the N8N_BASIC_AUTH_PASSWORD value in the .env file"
  
  cd ..
fi

# Final instructions
print_message "Deployment completed successfully!"
print_message "Next steps:"
print_message "1. Update the frontend with the correct S3 bucket name"
print_message "2. Import the n8n workflows from the n8n/workflows directory"
print_message "3. Configure the API keys in the n8n .env file"
print_message "4. Verify AWS SES is set up for sending emails"
print_message "5. Run a test using the sample data generator:"
print_message "   python tools/generate_sample_data.py --users 10 --products 5 --db-insert"

exit 0
