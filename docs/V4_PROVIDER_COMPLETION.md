# Provider completion checkpoint - 27 November 2026

## Implemented and verified
- Opt-in local-model response cache in process RAM only: 32 entries, 4 MiB total, five-minute TTL. It keys the complete task data and schema together with the actual Ollama model digest, model/context and explicit prompt version. Editing source, contract, trace, schema or model digest prevents reuse.
- Cache hits return independent copies and are explicitly marked in usage; generation tokens for the current hit are zero. Cache clearing invalidates concurrent stale writes. Missing model revision bypasses the cache. No cache files or source keys are exposed through health.
- Alibaba Qwen Cloud adapter: explicit cloud consent, fixed allowlisted regional host construction, region/workspace/key configuration, local rate ledger, bounded request/response, no redirects/proxies/fallback/retries, and independent JSON-schema validation.
- Request IDs now survive usage extraction in all production adapters.
- Browser controls expose cache opt-in/clear and Qwen configuration state. Cloud source/code submission still requires the existing explicit consent control.

## Configuration
No cloud request was made in this checkpoint. Qwen Cloud remains unavailable until a user supplies region-matched settings:
- DASHSCOPE_API_KEY
- QWEN_CLOUD_WORKSPACE_ID
- QWEN_CLOUD_REGION: ap-southeast-1, us-east-1, cn-beijing, cn-hongkong or ap-northeast-1
- QWEN_CLOUD_MODEL: qwen-plus (default), qwen-turbo or qwen3.8-max

Select Qwen Cloud and the consent checkbox only when intending to send the necessary data to Alibaba. Configure settings outside the repository; never put keys in source, UI or logs. Provider account quotas and server-side termination are not inferred from local counters/cancellation.

## Verification
201 unit/integration tests passed, with one pre-existing Starlette warning. 21 real browser journeys passed with no page errors or external browser requests. Qwen wire/error/redirect/schema tests used a mocked transport and dummy credentials, not a live account.

A live local Qwen probe confirmed one real inference followed by a version-matched cache hit, then a miss after clearing. Its independent open-ended grammar check failed: the model proposed fixed length 1 where the task required an input-dependent length. The draft remained unapproved; that failure is retained and is not reported as success or general extraction accuracy.

## Primary API references checked
- Alibaba OpenAI-compatible chat: https://www.alibabacloud.com/help/en/model-studio/compatibility-of-openai-with-dashscope
- Alibaba JSON Object / JSON Schema modes: https://www.alibabacloud.com/help/en/model-studio/qwen-structured-output

JSON Object transport does not guarantee schema conformance; the application performs its own schema check. The selected regional workspace host must correspond to the API key's region.
