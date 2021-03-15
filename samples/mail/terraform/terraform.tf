//# ---------------------------------------------------------------------------------------------------------------------
//# EVENT BRIDGE
//# ---------------------------------------------------------------------------------------------------------------------
//
//resource "aws_cloudwatch_event_rule" "every_one_minute" {
//  count = local.mailmicroservice_when_stage
//  name = "${local.lambda_name}_every-one-minute"
//  description = "Fires ${local.lambda_name} every one minutes"
//  schedule_expression = "rate(1 minute)"
//  is_enabled = false
//}
//
//resource "aws_cloudwatch_event_target" "every_one_minute" {
//  count = local.mailmicroservice_when_stage
//  rule = aws_cloudwatch_event_rule.every_one_minute[0].name
//  target_id = "Id09b637df-986a-446c-a1f1-0abda01281f1"
//  arn = "arn:aws:execute-api:eu-west-1:935392763270:kliz2t3zze/dev/POST/send"
//}
//
//
//# ---------------------------------------------------------------------------------------------------------------------
//# OUTPUT
//# ---------------------------------------------------------------------------------------------------------------------
//
//
//
////