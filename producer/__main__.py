#!/usr/bin/env python
import asyncio
import concurrent.futures
import contextvars
import logging

import aiohttp
import boto3
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.app.async_app import AsyncApp

from utils import prepare_message_attributes, raise_for_results, env, retry_exp, setup_logging

app = AsyncApp(token=env('SLACK_BOT_TOKEN'))
sqs = boto3.resource('sqs')
queue = sqs.get_queue_by_name(QueueName='Slack')
thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=100)

message_attributes = contextvars.ContextVar('message_attributes')


@retry_exp
def put_on_sqs(text, attributes):
    logging.debug(f'Message attributes {attributes}')
    response = queue.send_message(MessageBody=text, MessageAttributes=attributes)
    return response


async def async_put_on_sqs(text):
    result = await asyncio.get_running_loop().run_in_executor(
        thread_pool, put_on_sqs, text, message_attributes.get()
    )
    return result


@retry_exp
async def download_file(link, session):
    response = await session.get(
        link,
        headers={'Authorization': f'Bearer {env("SLACK_BOT_TOKEN")}'}
    )
    response.raise_for_status()
    return response


async def get_files_and_put_on_sqs(files):
    async def get_file_and_put_on_sqs(_session, _file):
        link = _file["url_private_download"]
        logging.debug(f'File attached {link}')

        response = await download_file(link, _session)
        content = await response.read()

        await async_put_on_sqs(content.decode())

    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*(get_file_and_put_on_sqs(session, f) for f in files), return_exceptions=True)

    raise_for_results(results)


@app.event(
    {"type": "message"}
)
async def handle_message(body):
    event = body["event"]
    if event.get("subtype") == 'message_deleted':
        return

    logging.debug(f'Message received: {body}')

    text = event.get('text')
    files = event.get('files', [])
    message_attributes.set(prepare_message_attributes(event))

    tasks = []
    if text:
        tasks.append(
            asyncio.create_task(async_put_on_sqs(text))
        )
    if files:
        tasks.append(
            asyncio.create_task(get_files_and_put_on_sqs(files))
        )

    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        raise_for_results(results)


async def main():
    try:
        while True:
            while True:
                try:
                    handler = AsyncSocketModeHandler(app, env('SLACK_APP_TOKEN'))
                    await handler.start_async()
                except Exception as e:
                    logging.error('Exception occurred: {}'.format(e))
    except KeyboardInterrupt:
        thread_pool.shutdown(cancel_futures=True)
        logging.info('Ctrl + C pressed. Exiting...')


if __name__ == '__main__':
    setup_logging()

    asyncio.run(main())
