import logging.config
import traceback
import os
import time
import requests
import json
import boto3
from datetime import datetime, timedelta

error_slack_url = os.environ.get('ERROR_SLACK_URL', None)
error_slack_channel = os.environ.get('ERROR_SLACK_CHANNEL', None)
log_level = os.environ.get('LOG_LEVEL', 'ERROR')


def logger_level(level):
    if level == 'CRITICAL':
        return 50
    elif level == 'ERROR':
        return 40
    elif level == 'WARNING':
        return 30
    elif level == 'INFO':
        return 20
    elif level == 'DEBUG':
        return 10
    else:
        return 0

logger = logging.getLogger()
logger.setLevel(logger_level(log_level))


def lambda_handler(event, context):
    try:
        # get environ
        feedly_url = os.environ.get('FEEDLY_URL', None)
        feedly_token = os.environ.get('FEEDLY_TOKEN', None)
        table_name = os.environ.get('DYNAMO_TABLE', None)
        interval_minute = os.environ.get('INTERVAL_MINUTE', None)
        feed_count = int(os.environ.get('FEED_COUNT', 100))

        # feedly get feed
        if interval_minute is None:
            interval_time = datetime.now() - timedelta(days=7)
        else:
            interval_time = datetime.now() - timedelta(minutes=int(interval_minute))
        unix_time = int(time.mktime(interval_time.timetuple())) * 1000
        logger.debug(unix_time)
        headers = {'Authorization': feedly_token}
        response_stream = requests.get(
            '{url}&count={count}&newerThan={time}'.format(
                url=feedly_url,
                count=feed_count,
                time=unix_time
            ),
            headers=headers
        )
        stream_data = json.loads(response_stream.text)
        logger.debug(stream_data)

        if not ('items' in stream_data):
            return

        stream_datas = stream_data['items']

        # to dynamo
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(table_name)

        for stream in stream_datas:
            logger.debug(stream)
            item = {
                'id': stream['id'],
                'url': stream['alternate'][0]['href'],
                'title': stream['title'],
                'origin': stream['origin']['title']
            }
            if 'summary' in stream:
                item['summary'] = stream['summary']['content']

            response = table.put_item(
                Item=item
            )
            logger.debug(response)

    except:
        logger.error(traceback.format_exc())
        requests.post(
            error_slack_url,
            json.dumps(
                {
                    'text': 'feedly_to_dynamo error\n{message}'.format(
                        message=traceback.format_exc()
                    ),
                    'channel': error_slack_channel
                }
            )
        )

    finally:
        return event
