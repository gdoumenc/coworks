# ---------------------------------------------------------------------------------------------------------------------
# ASSETS ON AWS
# ---------------------------------------------------------------------------------------------------------------------

locals {
  samples_bucket = "coworks-samples"
  sample_name = "website-headless"
}

resource "aws_s3_bucket_object" "assets" {
  for_each = fileset(path.module, "../assets/**")
  bucket = local.samples_bucket
  key = format("${local.sample_name}/%s", trimprefix(each.value, "../"))
  source = each.key
  etag = filemd5(each.key)
  content_type = lookup(var.file_types, regexall("\\.[^\\.]+\\z", each.key)[0], "application/octet-stream")
  acl = "public-read"
  tags = {
    Infra = "project"
    Name = local.sample_name
    Creator = "terraform"
    Target = "bucket"
    Stage = "sample"
  }
}

resource "aws_s3_bucket_object" "images" {
  for_each = fileset(path.module, "../images/**")
  bucket = local.samples_bucket
  key = format("${local.sample_name}/%s", trimprefix(each.value, "../"))
  source = each.key
  etag = filemd5(each.key)
  content_type = lookup(var.file_types, regexall("\\.[^\\.]+\\z", each.key)[0], "application/octet-stream")
  acl = "public-read"
  tags = {
    Infra = "project"
    Name = local.sample_name
    Creator = "terraform"
    Target = "bucket"
    Stage = "sample"
  }
}

resource "aws_cloudfront_distribution" "coworks-headless" {
  count = terraform.workspace == "default" ? 1 : 0

  origin {
    domain_name = "${local.samples_bucket}.s3.amazonaws.com"
    origin_id = "S3-${local.samples_bucket}/${local.sample_name}"
    origin_path = "/${local.sample_name}"
  }

  enabled = true
  is_ipv6_enabled = true

  restrictions {
    geo_restriction {
      restriction_type = "whitelist"
      locations = ["FR"]
    }
  }

  //  aliases = ["morassuti.com", "morassuti.fr"]

  default_cache_behavior {
    allowed_methods = ["GET", "HEAD"]
    cached_methods = ["GET", "HEAD"]
    target_origin_id = "S3-${local.samples_bucket}/${local.sample_name}"

    viewer_protocol_policy = "allow-all"
    default_ttl = 0

    max_ttl = 86400

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Infra = "project"
    Name = local.sample_name
    Creator = "terraform"
    Target = "bucket"
    Stage = "all"
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# OUTPUT
# ---------------------------------------------------------------------------------------------------------------------

output "cloudfront" {
  value = {
    "cloudfront_domain_name" = terraform.workspace == "default" ? aws_cloudfront_distribution.coworks-headless[0].domain_name : ""
  }
}

