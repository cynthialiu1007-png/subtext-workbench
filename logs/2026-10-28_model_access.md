# Model access record, 2026-10-28

## Ollama cloud: retired model
Command: ollama run qwen3.5:397b-cloud "Say hello in one sentence."
Response: Error: qwen3.5:397b was retired on September 25, 2026. Try glm-5.3-flash:cloud. (ref: 46bc4e86-542c-44eb-a116-c7df8a60a2dc)

## Ollama cloud: catalog returned by https://ollama.com/api/tags
No Qwen model was listed.
kimi-k3
minimax-m2.7
glm-5.3
kimi-k2.7-code
glm-5.3-flash
deepseek-v4-pro:0813
gpt-oss:120b
gemma4:31b
nemotron-3-ultra
clef:27b
kimi-k2.6
gpt-oss:20b
mistral-large-4
deepseek-v4.1-flash:1017
nemotron-3-nano:30b
mistral-large-3:675b
nemotron-3-super
beam
muse-spark-open
minimax-m3
minimax-m3.1-flash
glm-5.2
deepseek-v4.1-flash

## Ollama cloud: paid credits required
Command: ollama run gpt-oss:120b-cloud "Say hello in one sentence."
Response: Error: 402 Payment Required: Add usage credits to use cloud models: https://ollama.com/plans (ref: 354513bf-dce5-4257-903d-f3ebbaefbf47)
Command: ollama run deepseek-v4-pro:0813-cloud "Say hello in one sentence."
Response: Error: 402 Payment Required: Add usage credits to use cloud models: https://ollama.com/plans (ref: d07404a5-1337-4b25-988f-29e7fcc60148)

## Local models
qwen3:8b   ID 500a1f067a9f   5.2 GB   eval rate 23.33 tokens/s (test on 2026-10-27)
qwen3:14b  ID bdbd181c33f2   eval rate 13.24 tokens/s (test on 2026-10-28)
