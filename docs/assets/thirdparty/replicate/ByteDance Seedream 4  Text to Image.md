---
title: "ByteDance Seedream 4 | Text to Image"
source: "https://replicate.com/bytedance/seedream-4/api"
author:
published:
created: 2025-11-11
description: "Unified text-to-image generation and precise single-sentence editing at up to 4K resolution"
tags:
  - "clippings"
---
Run replicate/bytedance-seedream-4.0 with an API

Use one of our client libraries to get started quickly.

Set the `REPLICATE_API_TOKEN` environment variable

```shell
export REPLICATE_API_TOKEN=r8_UPA**********************************
```

[

Learn more about authentication

](https://replicate.com/bytedance/seedream-4/api/learn-more#authentication)

Install Replicate’s Python client library

```shell
pip install replicate
```

[Learn more about setup](https://replicate.com/bytedance/seedream-4/api/learn-more#setup)

Run **bytedance/seedream-4** using Replicate’s API. Check out the model's [schema](https://replicate.com/bytedance/seedream-4/api/schema) for an overview of inputs and outputs.

```python
import replicate

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

[Learn more](https://replicate.com/bytedance/seedream-4/api/learn-more)