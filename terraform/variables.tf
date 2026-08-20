variable "aws_region" {
  description = "Région AWS (doit matcher AWS_DEFAULT_REGION de ton .env)"
  type        = string
  default     = "us-east-1"
}

variable "collection_name" {
  description = "Nom de la collection OpenSearch Serverless"
  type        = string
  default     = "smart-rag"
}

variable "principal_arn" {
  description = "ARN IAM qui doit pouvoir lire/écrire dans la collection. Avec IAM Identity Center (SSO), utilise l'ARN du RÔLE, pas celui de la session temporaire : arn:aws:iam::<account_id>:role/AWSReservedSSO_<NomDuRole>_<suffixe>. Récupère le suffixe exact avec `aws sts get-caller-identity --query Arn` (garde seulement la partie entre assumed-role/ et le prochain /)."
  type        = string
  # Pas de défaut volontairement — à renseigner explicitement dans terraform.tfvars
}