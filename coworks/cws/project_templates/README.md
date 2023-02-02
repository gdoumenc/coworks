### Instructions

Info : *This project was created by the cws new command.*

#### Run

To run the microservice locally :

```
$> CWS_STAGE=dev cws run
 * Stage: dev
 * Debug mode: off
 * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
```
Then on another terminal, enter :

```
$> curl -H "Authorization:to_be_set" -H "USER_KEY:test" http://localhost:5000/
project ready!
```

If you are testing your microservice in an IDE then set the root path to src/tech and
define the INSTANCE_RELATIVE_PATH to .. (there env_vars are defined in fact)

#### Deploy :

```
$> CWS_STAGE=dev cws -p tech deploy -b bucket_name -pn aws_profile
 * Workspace: dev
Copy files to S3  [####################################]  100% 0%
Terraform apply (Create API routes)                              
Terraform apply (Deploy API and Lambda for the dev stage)        
Deploy microservice  [####################################]  100%
terraform output
coworks_layers_id = "xxxx"

$> curl -H "Authorization:to_be_set" -H "USER_KEY:test" https://xxxx.execute-api.eu-west-1.amazonaws.com/dev
project ready!
```
