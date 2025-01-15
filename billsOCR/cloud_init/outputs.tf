#output "postgres_password" {
#    value = aws_db_instance.default.password
#    sensitive = true
#}
#output "postgres_username" {
#    value = aws_db_instance.default.username
#}
#output "postgres_endpoint" {
#    value = aws_db_instance.default.endpoint
#}
output "aws_access_key" {
    value = var.access_key
}
output "aws_secret_key" {
    value = var.secret_key
    sensitive = true
}
output "s3_bucket" {
    value = aws_s3_bucket.train_materials.bucket
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