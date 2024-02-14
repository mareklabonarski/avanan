#!/usr/bin/env python
import asyncio
import concurrent.futures
import logging
import os
import re
from contextlib import suppress

import boto3
import django
import django.db.utils
import django.core.exceptions
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from utils import retry_exp, env, raise_for_results, setup_logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'avanan.settings')
django.setup()

from web.models import SensitiveDataPattern, DataLeak


POOL_SIZE = 1000
MAX_MESSAGES = 10
PATTERN_UPDATE_INTERVAL = 30


semaphore = asyncio.Semaphore(POOL_SIZE)
sqs = boto3.resource('sqs')
queue = sqs.get_queue_by_name(QueueName='Slack')
thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=int(POOL_SIZE / MAX_MESSAGES))
user_client = AsyncWebClient(token=env('SLACK_USER_TOKEN'))
bot_client = AsyncWebClient(token=env('SLACK_BOT_TOKEN'))


_patterns = []


async def update_patterns(once=False):
    logging.info('Updating patterns...')

    global _patterns
    try:
        patterns = SensitiveDataPattern.objects.all().aiterator()
        _patterns = [p async for p in patterns]
    except Exception:
        logging.error("Could not update sensitive data patterns", exc_info=True)

    if not once:
        await asyncio.sleep(PATTERN_UPDATE_INTERVAL)
        await update_patterns()


def get_from_sqs():
    return queue.receive_messages(
        MaxNumberOfMessages=MAX_MESSAGES,
        WaitTimeSeconds=20,
        MessageAttributeNames=['All'],
    )


def find_data_leaks(message):
    data_leaks = []

    for pattern in _patterns:
        if match := re.match(pattern.compiled, message.body):
            content = match.group(1)
            data_leaks.append(
                DataLeak(
                    pattern=pattern, message=message.body, message_id=message.message_id, content=content)
            )
            logging.warning(
                f'Found data leak for pattern "{pattern}": "{content}" in message with id {message.message_id}')

    return data_leaks


@retry_exp
async def delete_chat_message(attributes):
    try:
        await user_client.chat_delete(
            **{name: attributes[name]['StringValue'] for name in ["channel", "ts"]}
        )
    except SlackApiError as e:
        if str(e) != "The server responded with: {'ok': False, 'error': 'message_not_found'}":
            raise


@retry_exp
async def post_chat_info(attributes):
    await bot_client.chat_postMessage(
        text=f"Message blocked due to Sensitive Data violation!",
        channel=attributes['channel']['StringValue']
    )


async def update_slack_history(attributes):
    tasks = [
        asyncio.create_task(
            delete_chat_message(attributes)
        ),
        asyncio.create_task(
            post_chat_info(attributes)
        )
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    raise_for_results(results)


async def detect_data_leak(message):
    logging.debug(f'Assessing message {message.body} {message.message_attributes}')

    # TODO spawn to sep process as could be cpu heavy when many patterns are to be checked
    if data_leaks := find_data_leaks(message):
        await update_slack_history(message.message_attributes)

        with suppress(django.db.utils.IntegrityError):
            await DataLeak.objects.abulk_create(data_leaks)

    await asyncio.get_running_loop().run_in_executor(
        thread_pool, retry_exp(message.delete)
    )


async def consume():
    messages = await asyncio.get_running_loop().run_in_executor(
        thread_pool, get_from_sqs
    )

    results = await asyncio.gather(*(detect_data_leak(m) for m in messages), return_exceptions=True)
    raise_for_results(results)


async def main():
    try:
        _ = asyncio.create_task(update_patterns())
        while True:
            while True:
                try:
                    async with semaphore:
                        await asyncio.create_task(consume())
                except Exception as e:
                    logging.error('Exception occurred: {}'.format(e), exc_info=True)
    except KeyboardInterrupt:
        logging.info('Ctrl + C pressed. Exiting')
        thread_pool.shutdown(cancel_futures=True)


if __name__ == '__main__':
    setup_logging()

    asyncio.run(main())
