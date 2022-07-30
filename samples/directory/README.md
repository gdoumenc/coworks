### Instructions

Define an user which must have the following policy:

```yaml
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "APIGatewayAccess",
            "Effect": "Allow",
            "Action": [
                "execute-api:ManageConnections",
                "execute-api:Invoke",
                "execute-api:InvalidateCache",
                "apigateway:GET"
            ],
            "Resource": [
                "arn:aws:apigateway:eu-west-1::/restapis/*",
                "arn:aws:apigateway:eu-west-1::/restapis"
            ]
        }
    ]
}
```

Then add a file ``vars.secret.json`` in the ``env_vars`` folder:

```yaml
{
  "AWS_USER_ACCESS_KEY_ID": AWS_USER_ACCESS_KEY_ID_VALUE,
  "AWS_USER_SECRET_ACCESS_KEY": AWS_USER_SECRET_ACCESS_KEY_VALUE
}
```
