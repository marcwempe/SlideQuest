---
title: "ByteDance Seedream 4 | Text to Image"
source: "https://replicate.com/bytedance/seedream-4/api/schema"
author:
published:
created: 2025-11-11
description: "Unified text-to-image generation and precise single-sentence editing at up to 4K resolution"
tags:
  - "clippings"
---
Run replicate/bytedance-seedream-4.0 with an API

## Input schema

size string

Image resolution: 1K (1024px), 2K (2048px), 4K (4096px), or 'custom' for specific dimensions.

Default

"2K"

width integer

Custom image width (only used when size='custom'). Range: 1024-4096 pixels.

Default

2048

Minimum

1024

Maximum

4096

height integer

Custom image height (only used when size='custom'). Range: 1024-4096 pixels.

Default

2048

Minimum

1024

Maximum

4096

prompt string

Text prompt for image generation

max\_images integer

Maximum number of images to generate when sequential\_image\_generation='auto'. Range: 1-15. Total images (input + generated) cannot exceed 15.

Default

1

Minimum

1

Maximum

15

image\_input array

Input image(s) for image-to-image generation. List of 1-10 images for single or multi-reference generation.

Default

\[\]

aspect\_ratio string

Image aspect ratio. Only used when size is not 'custom'. Use 'match\_input\_image' to automatically match the input image's aspect ratio.

Default

"match\_input\_image"

enhance\_prompt boolean

Enable prompt enhancement for higher quality results, this will take longer to generate.

Default

true

## Output schema

Type

uri\[\]