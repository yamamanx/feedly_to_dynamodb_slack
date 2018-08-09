import logging.config
import traceback
import os
import json
import requests


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
        slack_url = os.environ.get('SLACK_URL', None)
        slack_channel = os.environ.get('SLACK_CHANNEL', None)

        teams_url = os.environ.get('TEAMS_URL', None)

        # data to slack
        if not('Records' in event):
            return event

        records = event['Records']
        for record in records:

            if not('dynamodb' in record):
                continue

            if not('NewImage' in record['dynamodb']):
                continue

            feed = record['dynamodb']['NewImage']
            url = feed['url']['S']
            title = feed['title']['S']
            origin = feed['origin']['S']

            if 'summary' in feed:
                summary = feed['summary']['S'][0:100] + '....'
            else:
                summary = ''

            requests.post(
                slack_url,
                json.dumps(
                    {
                        'channel': slack_channel,
                        'attachments': [
                            {
                                'author_name': origin,
                                'title': title,
                                'title_link': url,
                                'text': summary
                            }
                        ]
                    }
                )
            )

            #data to teams
            requests.post(
                teams_url,
                json.dumps(
                    {
                        'title': title,
                        'text': '[{summary}]({url})'.format(
                            summary=summary,
                            url=url
                        )
                    }
                )
            )

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