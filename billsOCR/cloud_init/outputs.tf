output "aws_access_key" {
    value = var.access_key
}
output "aws_secret_key" {
    value = var.secret_key
    sensitive = true
}
### MLflow
output "mlflow_uri" {
    value = "postgresql://${aws_db_instance.mlflow_backend.username}:${aws_db_instance.mlflow_backend.password}@${aws_db_instance.mlflow_backend.endpoint}/${aws_db_instance.mlflow_backend.db_name}"
    sensitive = true
}
### Transaction data
output "transaction_endpoint" {
    value = aws_db_instance.transaction_db.endpoint
}
output "transaction_username" {
    value = aws_db_instance.transaction_db.username
}
output "transaction_password" {
    value = aws_db_instance.transaction_db.password
    sensitive = true
}
### Train materials bucket
output "materials_bucket" {
    value = aws_s3_bucket.train_materials.bucket
}
### App raw data bucket
output "app_data_bucket" {
    value = aws_s3_bucket.app_data.bucket
}
#output "mongo_connection_string" { 
#    value = mongodbatlas_cluster.bills_cluster.connection_strings.0.standard_srv 
#}
#output "mongo_username" { 
#    value = mongodbatlas_database_user.billsdb_user.username 
#} 
#output "mongo_password" { 
#    value = mongodbatlas_database_user.billsdb_user.password 
#    sensitive = true
#}