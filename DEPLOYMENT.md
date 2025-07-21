# Loan Eligibility Engine Deployment Guide

This guide provides step-by-step instructions for deploying the Loan Eligibility Engine on AWS Free Tier.

## Prerequisites

Before you begin, ensure you have the following:

1. **AWS Account** with Free Tier access
2. **AWS CLI** installed and configured with appropriate credentials
3. **Serverless Framework** installed (`npm install -g serverless`)
4. **Docker** and **Docker Compose** installed (for n8n)
5. **Python 3.9+** installed
6. **PostgreSQL Client** installed (for database initialization)

## Deployment Steps

### 1. Clone the Repository

```bash
git clone <repository-url>
cd loan-eligibility-engine
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure AWS Credentials

Ensure your AWS credentials are properly configured:

```bash
aws configure
```

### 4. Deploy Using the Automated Script

The simplest way to deploy is using the provided deployment script:

```bash
chmod +x deploy.sh
./deploy.sh
```

This script will:
- Deploy AWS resources using Serverless Framework
- Initialize the database schema
- Set up n8n using Docker Compose

### 5. Manual Deployment Steps

If you prefer to deploy manually or need to customize the deployment, follow these steps:

#### 5.1. Deploy AWS Resources

```bash
cd infrastructure
serverless deploy --stage dev --region us-east-1
```

Note the outputs from the deployment, including:
- S3 Bucket name
- RDS Endpoint and Port

#### 5.2. Initialize the Database

Get the database password from AWS SSM Parameter Store:

```bash
DB_PASSWORD=$(aws ssm get-parameter --name "/loan-eligibility/db-password" --with-decryption --region us-east-1 --query "Parameter.Value" --output text)
export PGPASSWORD=$DB_PASSWORD
```

Apply the database schema:

```bash
psql -h <rds-endpoint> -p <rds-port> -U admin -d loaneligibility -f schema.sql
```

#### 5.3. Deploy n8n

Create the `.env` file in the `n8n` directory:

```bash
cd ../n8n
```

Create a `.env` file with the following content:

```
# n8n Configuration
N8N_PORT=5678
N8N_PROTOCOL=http
N8N_HOST=localhost
N8N_ENCRYPTION_KEY=<generate-random-key>
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=<secure-password>

# Database Configuration
POSTGRES_USER=admin
POSTGRES_PASSWORD=<db-password-from-ssm>
POSTGRES_DB=n8n
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# AWS Configuration
AWS_ACCESS_KEY_ID=<your-aws-access-key>
AWS_SECRET_ACCESS_KEY=<your-aws-secret-key>
AWS_REGION=us-east-1

# API Keys
OPENAI_API_KEY=<your-openai-api-key>
GEMINI_API_KEY=<your-gemini-api-key>

# Email Configuration
SENDER_EMAIL=notifications@loaneligibility.example.com
```

Start n8n using Docker Compose:

```bash
docker-compose up -d
```

### 6. Import n8n Workflows

1. Access the n8n web interface at `http://localhost:5678`
2. Log in with the credentials from your `.env` file
3. Import each workflow from the `n8n/workflows` directory:
   - `workflow_a_loan_discovery.json`
   - `workflow_b_user_loan_matching.json`
   - `workflow_c_user_notification.json`
   - `main_workflow.json`

### 7. Configure AWS SES for Email Notifications

1. Verify your sender email address in AWS SES:

```bash
aws ses verify-email-identity --email-address notifications@loaneligibility.example.com --region us-east-1
```

2. If you're in the SES sandbox, also verify recipient email addresses:

```bash
aws ses verify-email-identity --email-address recipient@example.com --region us-east-1
```

### 8. Update Frontend Configuration

Update the S3 bucket name in the frontend code:

```bash
cd ../frontend
```

Edit `js/app.js` to update the S3 bucket name with the one from your deployment.

### 9. Test the Deployment

Use the provided test script to validate your deployment:

```bash
cd ../tools
python test_system.py --users 10 --products 5
```

This script will:
1. Generate sample user data and loan products
2. Upload user data to S3
3. Monitor the database for processing
4. Validate the results

### 10. Monitoring and Maintenance

#### CloudWatch Logs

Monitor AWS Lambda functions using CloudWatch Logs:

```bash
aws logs filter-log-events --log-group-name "/aws/lambda/loan-eligibility-engine-dev-processUserData" --region us-east-1
```

#### n8n Execution Logs

View workflow execution logs in the n8n web interface:
1. Go to `http://localhost:5678`
2. Navigate to the "Executions" tab

#### Database Maintenance

Connect to the PostgreSQL database:

```bash
export PGPASSWORD=$DB_PASSWORD
psql -h <rds-endpoint> -p <rds-port> -U admin -d loaneligibility
```

Useful SQL queries for monitoring:
- `SELECT COUNT(*) FROM users;` - Count users
- `SELECT COUNT(*) FROM loan_products;` - Count loan products
- `SELECT COUNT(*) FROM matches;` - Count matches
- `SELECT COUNT(*) FROM notifications;` - Count notifications

## Troubleshooting

### Common Issues

1. **S3 Upload Failures**
   - Check IAM permissions for the Lambda function
   - Verify CORS configuration on the S3 bucket

2. **Database Connection Issues**
   - Ensure the security group allows connections on port 5432
   - Verify database credentials in environment variables

3. **n8n Workflow Failures**
   - Check webhook URLs are correctly configured
   - Verify API keys are properly set in the `.env` file

4. **Email Notification Issues**
   - Confirm SES is properly configured and email addresses are verified
   - Check SES sending limits in your AWS account

### Getting Help

If you encounter issues not covered in this guide:

1. Check the CloudWatch Logs for Lambda function errors
2. Review the n8n execution logs for workflow errors
3. Examine the Docker logs for n8n container issues:
   ```bash
   docker-compose logs -f n8n
   ```

## Security Considerations

1. **Database Security**
   - The RDS instance is publicly accessible for development purposes
   - For production, consider restricting access using security groups

2. **API Keys**
   - Store API keys securely in environment variables or AWS SSM Parameter Store
   - Rotate keys regularly

3. **Authentication**
   - n8n is protected with basic authentication
   - For production, consider adding additional security layers

4. **Data Protection**
   - User data is stored in PostgreSQL
   - Consider encrypting sensitive data at rest

## Cost Optimization

This deployment is designed to stay within AWS Free Tier limits:

- RDS: Uses db.t3.micro instance (free for 12 months)
- Lambda: Stays within free tier execution limits
- S3: Minimal storage usage within free tier
- SES: Free tier includes 62,000 outbound messages per month

Monitor your AWS Billing Dashboard regularly to ensure you stay within free tier limits.

## Next Steps

After successful deployment, consider:

1. **Adding Monitoring**: Set up CloudWatch Alarms for key metrics
2. **Implementing CI/CD**: Automate deployments using GitHub Actions or AWS CodePipeline
3. **Enhancing Security**: Add API Gateway with proper authentication
4. **Scaling**: Optimize database queries and Lambda functions for larger datasets
