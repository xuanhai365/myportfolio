resource "random_string" "bills_password" {
    length = 10
    upper = true
    numeric = true
    special = true
}
resource "aws_db_instance" "default" {
    allocated_storage = 10
    db_name = "billsOCR"
    engine = "postgres"
    instance_class = "db.t3.micro"
    skip_final_snapshot = true
    username = "bills"
    password = "${random_string.bills_password.result}"
}