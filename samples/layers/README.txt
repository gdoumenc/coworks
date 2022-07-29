This project was created by the cws new command.

To run the microservice locally :

$> cws -p src/tech run

Then on another terminal, enter :

$> curl -H "Authorization:to_be_set" -H "USER_KEY:test" http://localhost:5000/

To deploy :

$> cws -p src/tech deploy -b bucket_name -pn aws_profile -l arn:aws:lambda:eu-west-1:935392763270:layer:coworks-VERSION

To destroy the created service :

$> terraform -chdir=terraform destroy
