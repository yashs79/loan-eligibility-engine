# Loan Eligibility Engine

An automated system that ingests user data, discovers personal loan products from public websites, matches users to eligible products, and notifies them.

## Features

- Scalable CSV data ingestion via S3 and Lambda
- Web crawling for loan product discovery using n8n
- Multi-stage matching algorithm with LLM optimization
- Automated user notifications via AWS SES
- Minimal UI for CSV upload

## Tech Stack

- **Backend**: Python 3.9+
- **Cloud**: AWS (S3, Lambda, RDS PostgreSQL, SES)
- **Workflow Automation**: n8n (self-hosted via Docker)
- **AI**: Google Gemini or OpenAI GPT API
- **Deployment**: Serverless Framework & Docker Compose
- **Frontend**: Simple HTML/CSS/JS for CSV upload

## Project Structure

```
loan-eligibility-engine/
├── backend/              # Python Lambda functions
├── frontend/             # Minimal UI for CSV upload
├── infrastructure/       # Serverless Framework configuration
├── n8n/                  # Docker setup for n8n
├── ARCHITECTURE.md       # Detailed system architecture
└── README.md             # This file
```

## Setup Instructions

### Prerequisites

- AWS Account (Free Tier eligible)
- Docker and Docker Compose
- Node.js and Serverless Framework
- Python 3.9+

### Installation

1. **Clone the repository**

```bash
git clone <repository-url>
cd loan-eligibility-engine
```

2. **Set up AWS credentials**

```bash
aws configure
```

3. **Deploy AWS infrastructure**

```bash
cd infrastructure
npm install
serverless deploy
```

4. **Start n8n instance**

```bash
cd ../n8n
docker-compose up -d
```

5. **Deploy frontend**

```bash
cd ../frontend
# Follow frontend deployment instructions
```

## Usage

1. Access the frontend UI to upload CSV files with user data
2. The system will automatically process the data and trigger the matching workflow
3. Users will receive email notifications about eligible loan products

## Development

### Local Development

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run local API for testing
serverless offline
```

### Deploying Changes

```bash
# Deploy AWS resources
cd infrastructure
serverless deploy

# Update n8n workflows
# Import the workflow JSON files through the n8n UI
```

## License

MIT
