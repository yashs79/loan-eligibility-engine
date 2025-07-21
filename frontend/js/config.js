// AWS Configuration
const awsConfig = {
    region: 'us-east-1', // Update with your AWS region
    bucketName: 'loan-eligibility-engine-user-data-dev', // Update with your S3 bucket name
    identityPoolId: 'YOUR_IDENTITY_POOL_ID', // Update with your Cognito Identity Pool ID
};

// API Configuration
const apiConfig = {
    // If using API Gateway for additional functionality
    apiUrl: 'https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/dev',
};

// Initialize AWS SDK
function initAWS() {
    AWS.config.region = awsConfig.region;
    
    // Configure AWS credentials using Cognito Identity Pool
    AWS.config.credentials = new AWS.CognitoIdentityCredentials({
        IdentityPoolId: awsConfig.identityPoolId,
    });
}

// Initialize AWS SDK when the script loads
initAWS();
