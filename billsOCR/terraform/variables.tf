variable "region" {
    description = "AWS region"
    type = string
}
variable "access_key" {
    description = "AWS access key"
    type = string
}
variable "secret_key" {
    description = "AWS secret key"
    type = string
}
variable "vpc_ip" {
    description = "AWS VPC IP"
    type = string
}
variable "public_sub" {
    description = "AWS VPC public subnet"
    type = list(string)
}
variable "private_sub" {
    description = "AWS VPC private subnet"
    type = list(string)
}
variable "mongodbatlas_public_key" {
    description = "MongoDB Atlas public key"
    type = string
}
variable "mongodbatlas_private_key" {
    description = "MongoDB Atlas private key"
    type = string
}
variable "atlas_org_id" {
    description = "MongoDB Atlas Org Id"
    type = string
}