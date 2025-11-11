---
title: "ByteDance Seedream 4 | Text to Image"
source: "https://replicate.com/bytedance/seedream-4/api/learn-more"
author:
published:
created: 2025-11-11
description: "Unified text-to-image generation and precise single-sentence editing at up to 4K resolution"
tags:
  - "clippings"
---
Run replicate/bytedance-seedream-4.0 with an API

## Authentication

Whenever you make an API request, you need to authenticate using a token. A token is like a password that uniquely identifies your account and grants you access.

The following examples all expect your Replicate access token to be available from the command line. Because tokens are secrets, they should not be in your code. They should instead be stored in [environment variables](https://12factor.net/config). Replicate clients look for the `REPLICATE_API_TOKEN` environment variable and use it if available.

To set this up you can use:

```shell
export REPLICATE_API_TOKEN=r8_UPA**********************************
```

Some application frameworks and tools also support a text file named `.env` which you can edit to include the same token:

```
REPLICATE_API_TOKEN=r8_UPA**********************************
```

The Replicate API uses the `Authorization` HTTP header to authenticate requests. If you’re using a [client library](https://replicate.com/docs/reference/client-libraries) this is handled for you.

You can test that your access token is setup correctly by using our [`account.get`](https://replicate.com/docs/reference/http#account.get) endpoint:

```bash
curl https://api.replicate.com/v1/account -H "Authorization: Bearer $REPLICATE_API_TOKEN"
# {"type":"user","username":"aron","name":"Aron Carroll","github_url":"https://github.com/aron"}
```

If it is working correctly you will see a JSON object returned containing some information about your account, otherwise ensure that your token is available:

```bash
echo "$REPLICATE_API_TOKEN"
# "r8_xyz"
```

## Setup

First you’ll need to ensure you have a Python environment setup:

```
python -m venv .venv
source .venv/bin/activate
```

Then install the `replicate` [Python library](https://github.com/replicate/replicate-python):

```
pip install replicate
```

In a main.py file, import `replicate`:

```python
import replicate
```

This will use the `REPLICATE_API_TOKEN` API token you’ve set up in your environment for authorization.

## Run the model

Use the `replicate.run()` method to run the model:

```python
input = {
    "prompt": "a photo of a store front called \"Seedream 4\", it sells books, a poster in the window says \"Seedream 4 now on Replicate\"",
    "aspect_ratio": "4:3"
}

output = replicate.run(
    "bytedance/seedream-4",
    input=input
)

# To access the file URLs:
print(output[0].url())
#=> "https://replicate.delivery/.../output_0.jpg"

# To write the files to disk:
for index, item in enumerate(output):
    with open(f"output_{index}.jpg", "wb") as file:
        file.write(item.read())
#=> output_0.jpg written to disk
```

You can learn about pricing for this model on the [model page](https://replicate.com/replicate/bytedance-seedream-4.0).

The `run()` function returns the output directly, which you can then use or pass as the input to another model. If you want to access the full prediction object (not just the output), use the `replicate.predictions.create()` method instead. This will return a `Prediction` object that includes the prediction id, status, logs, etc.

## Prediction lifecycle

Running predictions and trainings can often take significant time to complete, beyond what is reasonable for an HTTP request/response.

When you run a model on Replicate, the prediction is created with a `“starting”` state, then instantly returned. This will then move to `"processing"` and eventual one of `“successful”`, `"failed"` or `"canceled"`.

Starting

Running

Succeeded

Failed

Canceled

You can explore the prediction lifecycle by using the `prediction.reload()` method update the prediction to it's latest state.

Show example

```python
import time

prediction = replicate.predictions.create(
  model="bytedance/seedream-4",
  input=input
)
#=> Prediction(id='z3wbih3bs64of7lmykbk7tsdf4', status="starting", ...)

prediction.reload()
#=> Prediction(id='z3wbih3bs64of7lmykbk7tsdf4', status="processing", ...)

for i in range(5):
  prediction.reload()
  if prediction.status in {"succeeded", "failed", "canceled"}:
    break

  # Wait for 2 seconds and then try again.
  time.sleep(2)

print(prediction);
#=> Prediction(id='z3wbih3bs64of7lmykbk7tsdf4', status="successful", ...)
```

## Webhooks

Webhooks provide real-time updates about your prediction. Specify an endpoint when you [create a prediction](https://replicate.com/docs/reference/http#predictions.create), and Replicate will send HTTP POST requests to that URL when the prediction is created, updated, and finished.

It is possible to provide a URL to the `predictions.create()` function that will be requested by Replicate when the prediction status changes. This is an alternative to polling.

To receive webhooks you’ll need a web server. The following example uses [AIOHTTP](https://docs.aiohttp.org/en/stable/index.html), a basic webserver built on top of Python’s asyncio library, but this pattern will apply to most frameworks.

Show example

```python
from aiohttp import web

# NOTE: This should point to the internet facing endpoint for your application.
callback_url = "https://my.app/webhooks/replicate"

# Create a python webserver using aiohttp to handle the webhook and push
# the completed prediction into our queue.
routes = web.RouteTableDef()

# Add a request handler at /webhooks/replicate to receive the request.
@routes.post('/webhooks/replicate')
async def callback_replicate(request):
  prediction = await request.json()
  print(prediction)
  #=> Prediction(id='z3wbih3bs64of7lmykbk7tsdf4', ...)
  return web.Response(text="OK")

# Start the webserver.
app = web.Application()
app.add_routes(routes)

web.run_app(app)
```

Then create the prediction passing in the webhook URL and specify which events you want to receive out of `"start"`, `"output"` `”logs”` and `"completed"`.

```python
input = {
    "prompt": "a photo of a store front called \"Seedream 4\", it sells books, a poster in the window says \"Seedream 4 now on Replicate\"",
    "aspect_ratio": "4:3"
}

callback_url = "https://my.app/webhooks/replicate"
replicate.predictions.create(
  model="bytedance/seedream-4",
  input=input,
  webhook=callback_url,
  webhook_events_filter=["completed"]
)

# The server will now handle the event and log:
#=> Prediction(id='z3wbih3bs64of7lmykbk7tsdf4', ...)
```

From a security perspective it is also possible to verify that the webhook came from Replicate, check out our documentation on [verifying webhooks](https://replicate.com/docs/webhooks#verifying-webhooks) for more information.

## Access a prediction

You may wish to access the prediction object. In these cases it’s easier to use the `replicate.predictions.create()` function, which return the prediction object.

Though note that these functions will only return the created prediction, and it will not wait for that prediction to be completed before returning. Use `replicate.predictions.get()` to fetch the latest prediction.

```python
import replicate

input = {
    "prompt": "a photo of a store front called \"Seedream 4\", it sells books, a poster in the window says \"Seedream 4 now on Replicate\"",
    "aspect_ratio": "4:3"
}

prediction = replicate.predictions.create(
  model="bytedance/seedream-4",
  input=input
)
#=> Prediction(id='z3wbih3bs64of7lmykbk7tsdf4', ...)
```

## Cancel a prediction

You may need to cancel a prediction. Perhaps the user has navigated away from the browser or canceled your application. To prevent unnecessary work and reduce runtime costs you can use `prediction.cancel()` method to call the `predictions.cancel` endpoint.

```python
input = {
    "prompt": "a photo of a store front called \"Seedream 4\", it sells books, a poster in the window says \"Seedream 4 now on Replicate\"",
    "aspect_ratio": "4:3"
}

prediction = replicate.predictions.create(
  model="bytedance/seedream-4",
  input=input
)

prediction.cancel()
```

## Async Python methods

[asyncio](https://docs.python.org/3/library/asyncio.html) is a module built into Python's standard library for writing concurrent code using the async/await syntax.

Replicate's Python client has support for `asyncio`. Each of the methods has an async equivalent prefixed with `async_<name>`.

```python
input = {
    "prompt": "a photo of a store front called \"Seedream 4\", it sells books, a poster in the window says \"Seedream 4 now on Replicate\"",
    "aspect_ratio": "4:3"
}

prediction = replicate.predictions.create(
  model="bytedance/seedream-4",
  input=input
)

prediction = await replicate.predictions.async_create(
  model="bytedance/seedream-4",
  input=input
)
```