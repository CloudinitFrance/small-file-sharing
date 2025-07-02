# 🚀 SmallFileSharing - Serverless File Sharing on AWS

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![AWS](https://img.shields.io/badge/AWS-Serverless-orange)](https://aws.amazon.com/)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)

> A production-ready serverless file sharing solution built on AWS, featuring enterprise-grade security with Cognito authentication, RESTful API design, and automatic email notifications.

## 🎯 Key Features

- **🔒 Secure Authentication**: JWT-based authentication via AWS Cognito
- **📁 File Management**: Upload, list, delete, and share files up to 10MB
- **📧 Email Notifications**: Automatic email delivery with time-limited download links
- **🏗️ Serverless Architecture**: Zero infrastructure management with automatic scaling
- **💰 Cost-Effective**: Pay only for what you use with AWS Lambda
- **🔗 RESTful API**: Clean, intuitive API design with comprehensive documentation

## 🏛️ Architecture Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Client    │────▶│ API Gateway  │────▶│   Lambda    │
└─────────────┘     └──────────────┘     └─────────────┘
                            │                     │
                            ▼                     ▼
                    ┌──────────────┐     ┌─────────────┐
                    │   Cognito    │     │  DynamoDB   │
                    └──────────────┘     └─────────────┘
                                                 │
                                                 ▼
                                         ┌─────────────┐
                                         │     S3      │
                                         └─────────────┘
                                                 │
                                                 ▼
                                         ┌─────────────┐
                                         │     SES     │
                                         └─────────────┘
```

## 🚀 Quick Start

### Prerequisites

- AWS Account with appropriate permissions
- [CognitoApi](https://github.com/CloudinitFrance/cognito-api/) installed and configured
- Python 3.8+ for local development
- AWS CLI configured

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/CloudinitFrance/small-file-sharing.git
   cd small-file-sharing
   ```

2. **Deploy CognitoApi** (if not already done)
   ```bash
   # Follow the CognitoApi installation guide
   # https://github.com/CloudinitFrance/cognito-api#installation
   ```

3. **Create AWS Resources**
   
   Use our automated setup script or follow the manual steps:
   
   ```bash
   # Coming soon: Terraform/CloudFormation templates
   ```

   **Manual Setup:**
   - S3 Bucket: `your-file-sharing-bucket-name`
   - DynamoDB Table: `your-files-table` (partition key: `file_id`)
   - Lambda Functions: Deploy all 4 functions from `/endpoints`
   - API Gateway: Configure routes as specified below

## 📚 API Documentation

### Authentication
All endpoints require:
- `x-api-key` header
- `Authorization: Bearer {IdToken}` header

### Endpoints

#### 📤 Upload File
```http
POST /v1/users/{user_id}/files
Content-Type: application/json

{
  "file_data": "base64_encoded_data",
  "remote_file_name": "document.pdf"
}
```

#### 📋 List Files
```http
GET /v1/users/{user_id}/files
```

#### 🗑️ Delete File
```http
DELETE /v1/users/{user_id}/files/{file_id}
```

#### 📨 Share File
```http
POST /v1/users/{user_id}/files/{file_id}/share
Content-Type: application/json

{
  "share_with": ["email1@example.com", "email2@example.com"]
}
```

## 🛠️ Development

### Project Structure
```
small-file-sharing/
├── endpoints/
│   ├── upload-file/
│   ├── get-user-files/
│   ├── delete-user-file/
│   └── share-file/
├── postman/
└── README.md
```

### Testing
Import the Postman collection from `/postman` directory and configure:
- `API_BASE_URL`: Your API Gateway URL
- `API_KEY`: Your generated API key
- `IdToken`: From CognitoApi authentication

## 🔒 Security Features

- JWT validation on every request
- User isolation (users can only access their own files)
- Time-limited presigned URLs (1 hour expiry)
- API key requirement for additional security
- Input validation using JSON schemas

## 🚧 Roadmap

- [ ] Infrastructure as Code templates (Terraform/CloudFormation)
- [ ] Support for larger files
- [ ] File encryption at rest
- [ ] File sharing permissions management

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/CloudinitFrance/small-file-sharing/blob/main/LICENSE) file for details.

## 👨‍💻 Author

**Tarek CHEIKH**
- GitHub: [@CloudinitFrance](https://github.com/CloudinitFrance)
- LinkedIn: [Tarek CHEIKH](https://fr.linkedin.com/in/tarekouldcheikh)
- Website: [cloudinit.fr](https://cloudinit.fr)

---

⭐ If you find this project useful, please consider giving it a star on GitHub!
