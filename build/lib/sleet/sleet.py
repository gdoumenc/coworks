import datetime
import json


class SleetMicroServiceError(Exception):
    def __init__(self, msg):
        super().__init__()
        self.__msg = msg

    @property
    def msg(self):
        return self.__msg


class SleetAwsMicroService:

    def __init__(self, *, logger=None):
        self.logger = logger

    def logger_info(self, msg, *args, **kwargs):
        if self.logger:
            self.logger.info(msg, *args, **kwargs)

    def lambda_handler(self, event, context):
        if 'httpMethod' in event:
            self.logger_info(f"Start API command {datetime.datetime.now()}")
            try:
                result = self.api_handler(event, context)
                self.logger_info(f"API command done {datetime.datetime.now()}")
                if not result:
                    return {
                        'isBase64Encoded': False,
                        'statusCode': 404,
                        'headers': {},
                        'body': json.dumps([])
                    }

                return {
                    'isBase64Encoded': False,
                    'statusCode': 200,
                    'headers': {},
                    'body': json.dumps(result)
                }
            except SleetMicroServiceError as e:
                self.logger_info(f"API command done {datetime.datetime.now()} with microservice error {str(e)}")
                return {
                    'isBase64Encoded': False,
                    'statusCode': 404,
                    'headers': {},
                    'body': json.dumps(e.msg)
                }
            except Exception as e:
                self.logger_info(f"API command done {datetime.datetime.now()} with error {str(e)}")
                return {
                    'isBase64Encoded': False,
                    'statusCode': 400,
                    'headers': {},
                    'body': json.dumps(str(e))
                }

        elif 'Records' in event:
            self.logger_info(f"Start SQS command {datetime.datetime.now()}")
            res = self.sqs_handler(event, context)
            self.logger_info(f"Command SQS done {datetime.datetime.now()}")
        else:
            res = "Undefined triggerring"
        return res

    def api_handler(self, event, context):
        raise NotImplementedError("api_handler not defined")

    def sqs_handler(self, event, context):
        raise NotImplementedError("sqs_handler not defined")
