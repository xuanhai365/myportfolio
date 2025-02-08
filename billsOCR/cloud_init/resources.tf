#data "aws_availability_zones" "available" {}
data "aws_security_group" "default" {
  name = "default"
}
#resource "aws_vpc" "bills_vpc" {
#    cidr_block = var.vpc_ip
#    tags = {
#        Name = "BillsOCR VPC"
#    }
#}
#resource "aws_subnet" "public_subnets" {
#    count = length(var.public_sub)
#    vpc_id = "${aws_vpc.bills_vpc.id}"
#    cidr_block = element(var.public_sub, count.index)
#    availability_zone = "${data.aws_availability_zones.available.names[count.index]}"
#}
#resource "aws_db_subnet_group" "db_subnet_group" {
#    name = "db_subnet_group"
#    subnet_ids = [aws_subnet.public_subnets[0].id, aws_subnet.public_subnets[1].id]
#}
#resource "aws_subnet" "private_subnets" {
#    count = length(var.private_sub)
#    vpc_id = "${aws_vpc.bills_vpc.id}"
#    cidr_block = element(var.private_sub, count.index)
#}
resource "random_password" "db_password" {
  length           = 16
  special          = false
}
#resource "aws_security_group" "bills_security" {
#  vpc_id      = "${aws_vpc.bills_vpc.id}"
#  name        = "billsocr_security"
#  description = "Allow all inbound for Postgres"
#ingress {
#    from_port   = 5432
#    to_port     = 5432
#    protocol    = "tcp"
#    cidr_blocks = ["0.0.0.0/0"]
#  }
#}

### AWS RDS setup
resource "aws_db_instance" "mlflow_backend" {
  allocated_storage = 10
  db_name = "billsocr-mlflow"
  engine = "postgres"
  instance_class = "db.t3.micro"
  skip_final_snapshot = true
  publicly_accessible = true
  username = "mlflow-backend"
  password = random_password.db_password.result
#  vpc_security_group_ids = [aws_security_group.bills_security.id]
#  db_subnet_group_name = aws_db_subnet_group.db_subnet_group.name
}
resource "aws_db_instance" "transaction_db" {
  allocated_storage = 10
  db_name = "billsocr-transaction"
  engine = "postgres"
  instance_class = "db.t3.micro"
  skip_final_snapshot = true
  publicly_accessible = true
  username = "transaction"
  password = random_password.db_password.result
}

### AWS S3 setup
resource "aws_s3_bucket" "train_materials" {
  bucket = "train-materials"
  force_destroy = true
}
resource "aws_s3_bucket" "app_data" {
  bucket = "raw-app-data"
  force_destroy = true
}

### AWS EC2 setup
data "aws_ami" "train_ami" {
  most_recent = true
  owners = ["amazon"]

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
  filter {
    name = "name"
    values = ["al2023-ami-202*"]
  }
}
resource "aws_instance" "train_instance" {
  ami           = data.aws_ami.train_ami.id
  instance_type = "t2.micro"
  vpc_security_group_ids = [data.aws_security_group.default.id]
  root_block_device {
    volume_size = 16
  }
  
  tags = {
    Name = "train-instance"
  }
}
resource "aws_instance" "inference_instance" {
  ami           = data.aws_ami.train_ami.id
  instance_type = "t2.micro"
  vpc_security_group_ids = [data.aws_security_group.default.id]
  root_block_device {
    volume_size = 16
  }
  
  tags = {
    Name = "inference-instance"
  }
}

### MongoDB setup
#resource "mongodbatlas_project" "bills_project" {
#  org_id = var.atlas_org_id
#  name = "billsdb"
#}
#resource "mongodbatlas_database_user" "billsdb_user" {
#  username = "bills"
#  password = random_password.bills_password.result
#  project_id = mongodbatlas_project.bills_project.id
#  auth_database_name = "admin"
#  roles {
#    role_name     = "readWrite"
#    database_name = "det_dataset"
#  }
#  roles {
#    role_name     = "readWrite"
#    database_name = "recog_dataset"
#  }
#}
#resource "mongodbatlas_project_ip_access_list" "ip" {
#  project_id = mongodbatlas_project.bills_project.id
#  cidr_block = "0.0.0.0/0"
#}
#resource "mongodbatlas_cluster" "bills_cluster" {
#  project_id   = mongodbatlas_project.bills_project.id
#  name         = "bills-cluster"
#  cluster_type = "REPLICASET"
#  replication_specs {
#    num_shards = 1
#    regions_config {
#      region_name     = upper(var.region)
#      electable_nodes = 3
#      priority        = 7
#      read_only_nodes = 0
#    }
#  }
#  # Provider Settings "block"
#  provider_instance_size_name = "M0"
#  provider_name               = "TENANT"
#  backing_provider_name       = "AWS"
#}