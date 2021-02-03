# ---------------------------------------------------------------------------------------------------------------------
# ASSETS ON AWS
# ---------------------------------------------------------------------------------------------------------------------

locals {
  samples_bucket = "coworks-samples"
  sample_name = "website-headless"
}

resource "aws_s3_bucket_object" "assets" {
  for_each = fileset(path.module, "../{assets,images}/**")
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

  origin {
    domain_name = "${aws_api_gateway_rest_api.website-handless[0].id}.execute-api.eu-west-1.amazonaws.com"
    origin_id = "API-${local.samples_bucket}/${local.sample_name}"
    origin_path = "/dev"
    custom_origin_config {
      http_port = 80
      https_port = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols = ["TLSv1"]
    }
  }

  aliases = ["*.morassuti.com", "morassuti.com"]
  price_class = "PriceClass_All"
  enabled = true
  is_ipv6_enabled = true

  restrictions {
    geo_restriction {
      restriction_type = "whitelist"
      locations = ["FR"]
    }
  }

  default_cache_behavior {
    allowed_methods = ["GET", "HEAD"]
    cached_methods = ["GET", "HEAD"]
    target_origin_id = "API-${local.samples_bucket}/${local.sample_name}"
    viewer_protocol_policy = "redirect-to-https"
    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
  }

  dynamic "ordered_cache_behavior" {
    for_each = ["assets", "images"]
    content {
      allowed_methods = ["GET", "HEAD"]
      cached_methods = ["GET", "HEAD"]
      target_origin_id = "S3-${local.samples_bucket}/${local.sample_name}"
      path_pattern = "${ordered_cache_behavior.value}/*"

      viewer_protocol_policy = "redirect-to-https"
      default_ttl = 0

      max_ttl = 86400

      forwarded_values {
        query_string = false
        cookies {
          forward = "none"
        }
      }
    }
  }

  viewer_certificate {
    acm_certificate_arn = "arn:aws:acm:us-east-1:935392763270:certificate/7907fef7-23c3-4ae2-900c-59fd8389ce95"
    ssl_support_method = "sni-only"
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

