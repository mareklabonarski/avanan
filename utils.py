import logging
import os

from tenacity import retry, wait_exponential


def setup_logging():
    logging.basicConfig(level=logging.DEBUG if env("DEBUG") else logging.INFO)


def prepare_message_attributes(event):
    return {
        'ts': {
            'StringValue': event['ts'],
            'DataType': 'String',
        },
        'user': {
            'StringValue': event['user'],
            'DataType': 'String',
        },
        'channel': {
            'StringValue': event['channel'],
            'DataType': 'String',
        }
    }


def raise_for_results(results):
    exceptions = list(filter(lambda e: isinstance(e, Exception), results))
    if exceptions:
        raise Exception(exceptions)


env = os.environ.get
retry_exp = retry(wait=wait_exponential(multiplier=1, min=4, max=10))
