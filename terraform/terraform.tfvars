# Récupéré depuis la console IAM → Rôles → AWSReservedSSO_AdministratorAccess_...
# Format IAM role (PAS le format sts::assumed-role/, qui donne une erreur 403
# avec OpenSearch Serverless Data Access Policy)
aws_region      ="us-east-1"
collection_name ="smart-rag"
principal_arn   ="arn:aws:iam::136609826386:role/aws-reserved/sso.amazonaws.com/us-west-2/AWSReservedSSO_AdministratorAccess_e4bb8ceea756d078"