Events from Slack are delivered throuh Events API Socket Mode
https://api.slack.com/apis/connections/events-api

, configured as on the screenshot below:
![Zrzut ekranu z 2024-02-29 21-03-19](https://github.com/mareklabonarski/avanan/assets/9976307/d8436b9c-138a-4f22-ba85-8942acf13f4e)

Producer uses this API through 
```
slack_bolt.adapter.socket_mode.async_handler.AsyncSocketModeHandler
from slack_bolt.app.async_app import AsyncApp

app = AsyncApp(token=env('SLACK_BOT_TOKEN'))
handler = AsyncSocketModeHandler(app, env('SLACK_APP_TOKEN'))
await handler.start_async()
```
So this is a correct socket based (websockets, not HTTP webhook) approach.

Description of the task clearly states, that in order to manage ocnfiguration and browse results, django admin can be used.
3. Create a simple Data Loss Prevention tool that given a file, open its content and try to look for patterns (for example: a credit card number), 
using a list of regular expressions, make it possible to manage those patterns using **django admin**
4. Use **django admin** to also show messages that were caught by the DLP tool, show the message, its content and the pattern that caught it.

In order to run it, best would be to use existing (my) credentials and the Slack application which I created and configured 
(added required permissions for desired events reception).
in main project folder, run:
```
docker-compose up
```

For the first time, you will have to wait couple of container restarts. First, db is being created, and other containers fail to connect to it, and will restart.
Later, schema migration will be run, and containers dependent on it will be restarting until the schema migration is completed.
Eventually all containers will be healthy and ready to work, you should be able to recognize it by looking at docker logs.

create superuser to login to admin:
```
docker-compose exec web python manage.py createsuperuser
```
Go to http://localhost:8000/admin/web/sensitivedatapattern/add/
and add following pattern: 
```
.*(4[0-9]{3} [0-9]{4} [0-9]{4} (?:[0-9]{4})?).*
```
This will detect Visa Cards numbers.
Now, you can go to slack and post a message '4056 2106 0266 6505' in #general.
It will be removed from chat and appropiate information will be displayed.


The sync boto3 api was calls are deferred to a thread executor, so that they don't block async loop on I/O...

