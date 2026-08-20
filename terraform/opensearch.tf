# US 2.1 — Provisionnement d'Amazon OpenSearch Serverless (Vector Engine)

# 1. Politique de chiffrement (obligatoire avant de créer la collection)
resource "aws_opensearchserverless_security_policy" "encryption" {
  name = "${var.collection_name}-encryption"
  type = "encryption"
  policy = jsonencode({
    Rules = [{
      ResourceType = "collection"
      Resource     = ["collection/${var.collection_name}"]
    }]
    AWSOwnedKey = true
  })
}

# 2. Politique réseau (accès public simple pour un PoC — à restreindre en prod)
resource "aws_opensearchserverless_security_policy" "network" {
  name = "${var.collection_name}-network"
  type = "network"
  policy = jsonencode([{
    Rules = [
      {
        ResourceType = "collection"
        Resource     = ["collection/${var.collection_name}"]
      },
      {
        ResourceType = "dashboard"
        Resource     = ["collection/${var.collection_name}"]
      }
    ]
    AllowFromPublic = true
  }])
}

# 3. Politique d'accès aux données — qui a le droit de lire/écrire (critère
# d'acceptation US 2.1 : "les politiques d'accès sont configurées pour
# autoriser le backend à lire et écrire")
resource "aws_opensearchserverless_access_policy" "data_access" {
  name = "${var.collection_name}-access"
  type = "data"
  policy = jsonencode([{
    Rules = [
      {
        ResourceType = "index"
        Resource     = ["index/${var.collection_name}/*"]
        Permission = [
          "aoss:CreateIndex",
          "aoss:DeleteIndex",
          "aoss:UpdateIndex",
          "aoss:DescribeIndex",
          "aoss:ReadDocument",
          "aoss:WriteDocument",
        ]
      },
      {
        ResourceType = "collection"
        Resource     = ["collection/${var.collection_name}"]
        Permission = [
          "aoss:CreateCollectionItems",
          "aoss:DescribeCollectionItems",
        ]
      }
    ]
    Principal = [var.principal_arn]
  }])
}

# 4. La collection elle-même, en mode VECTORSEARCH (obligatoire pour k-NN)
resource "aws_opensearchserverless_collection" "rag" {
  name = var.collection_name
  type = "VECTORSEARCH"

  depends_on = [
    aws_opensearchserverless_security_policy.encryption,
    aws_opensearchserverless_security_policy.network,
  ]
}

output "collection_endpoint" {
  description = "Endpoint à utiliser dans create_index.py et dans le backend"
  value       = aws_opensearchserverless_collection.rag.collection_endpoint
}

output "collection_arn" {
  value = aws_opensearchserverless_collection.rag.arn
}
