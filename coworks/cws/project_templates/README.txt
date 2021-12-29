This project was created by the cws new command.

The minimum command options to deploy :

$> cws deploy -b bucket_name -pn aws_profile -l arn:aws:lambda:eu-west-1:935392763270:layer:coworks-VERSION

To destroy the created service :

$> terraform -chdir=terraform destroy
