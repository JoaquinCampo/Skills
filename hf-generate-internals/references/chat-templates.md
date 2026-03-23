# Chat Templates

**Source**: `tokenization_utils_base.py`

## apply_chat_template()

```python
def apply_chat_template(
    self,
    conversation: list[dict[str, str]] | list[list[dict[str, str]]],
    tools: list[dict | Callable] | None = None,
    chat_template: str | None = None,
    add_generation_prompt: bool = False,
    continue_final_message: bool = False,
    tokenize: bool = True,
    padding: bool | str = False,
    truncation: bool = False,
    max_length: int | None = None,
    return_tensors: str | None = None,
    return_dict: bool = True,
    **kwargs,
) -> str | list[int] | BatchEncoding:
```

## How It Works

### 1. Template Resolution

Templates are Jinja2 strings stored in the tokenizer config:

```python
# Stored in tokenizer_config.json as "chat_template"
# Can be a single string or a dict of named templates:
{
    "chat_template": {
        "default": "{% for message in messages %}...",
        "tool_use": "{% for message in messages %}...(with tool calling)..."
    }
}
```

Resolution order:
1. `chat_template` argument (if provided)
2. `tokenizer.chat_template` (from config)
3. Default template (basic fallback)

When `tools` is provided and a `"tool_use"` template exists, it's selected
automatically.

### 2. Jinja2 Rendering

The template receives these variables:
- `messages`: the conversation list
- `add_generation_prompt`: boolean
- `bos_token`, `eos_token`: special tokens
- `tools`: tool definitions (if provided)

Example template (simplified Qwen2.5 style):
```jinja2
{% for message in messages %}
<|im_start|>{{ message['role'] }}
{{ message['content'] }}<|im_end|>
{% endfor %}
{% if add_generation_prompt %}
<|im_start|>assistant
{% endif %}
```

### 3. Tokenization

If `tokenize=True` (default), the rendered string is tokenized:
```python
# Internally calls:
self(rendered_text, return_tensors=return_tensors, padding=padding, ...)
```

If `tokenize=False`, returns the raw rendered string.

## add_generation_prompt=True

Appends the assistant turn header to the rendered template, so the model
knows to start generating as the assistant:

```
Without (add_generation_prompt=False):
  <|im_start|>system\nYou are helpful.<|im_end|>\n<|im_start|>user\nHello<|im_end|>\n

With (add_generation_prompt=True):
  <|im_start|>system\nYou are helpful.<|im_end|>\n<|im_start|>user\nHello<|im_end|>\n<|im_start|>assistant\n
```

**Always use `add_generation_prompt=True` when generating**. Without it,
the model doesn't know it should respond as the assistant, leading to
unpredictable behavior (it might continue as "user" or emit random roles).

## continue_final_message

Alternative to `add_generation_prompt`: instead of starting a new assistant
turn, it leaves the last message's closing token off so the model continues
that message:

```python
messages = [
    {"role": "user", "content": "What is 2+2?"},
    {"role": "assistant", "content": "The answer is"},  # partial
]

# continue_final_message=True: model continues "The answer is..."
# add_generation_prompt=True: model starts a NEW assistant message
```

**Cannot be used together with `add_generation_prompt`.**

## Common Patterns

### Two-Step: Render then Tokenize (Herald's pattern)

```python
messages = [{"role": "user", "content": "Solve: 2+3=?"}]

# Step 1: Render to string
chat_text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True,
)
# chat_text is a string like "<|im_start|>user\nSolve: 2+3=?\n<|im_end|>\n<|im_start|>assistant\n"

# Step 2: Tokenize separately
inputs = tokenizer(chat_text, return_tensors="pt").to(device)
input_len = inputs["input_ids"].shape[1]

# Step 3: Generate
outputs = model.generate(**inputs, max_new_tokens=512, ...)

# Step 4: Decode only generated tokens
generated_ids = outputs.sequences[0, input_len:]
text = tokenizer.decode(generated_ids, skip_special_tokens=True)
```

This two-step pattern gives access to the rendered text (useful for logging,
debugging) and precise control over `input_len` for slicing generated tokens.

### One-Step: Direct Tokenization

```python
inputs = tokenizer.apply_chat_template(
    messages,
    add_generation_prompt=True,
    tokenize=True,
    return_tensors="pt",
    return_dict=True,
).to(device)
# inputs is a BatchEncoding with input_ids and attention_mask

outputs = model.generate(**inputs, max_new_tokens=512)
```

Simpler but you don't get the rendered text string.

### Batched Chat Templates

```python
conversations = [
    [{"role": "user", "content": "Question 1"}],
    [{"role": "user", "content": "Question 2"}],
]

inputs = tokenizer.apply_chat_template(
    conversations,
    add_generation_prompt=True,
    tokenize=True,
    padding=True,           # left-pads for decoder-only
    return_tensors="pt",
    return_dict=True,
).to(device)
```

When batching, `padding=True` is required. For decoder-only models, ensure
the tokenizer is configured for left-padding:

```python
tokenizer.padding_side = "left"
```

## Gotchas

1. **pad_token required for batched generation**:
   ```python
   if tokenizer.pad_token is None:
       tokenizer.pad_token = tokenizer.eos_token
   ```

2. **Template varies by model**: Qwen uses `<|im_start|>/<|im_end|>`,
   Llama 3 uses `<|begin_of_text|>/<|eot_id|>`, etc. Always use
   `apply_chat_template` instead of manually formatting.

3. **System messages**: Not all models support system messages. The template
   may silently merge system into the first user message or ignore it.

4. **Special tokens in content**: The template handles special token
   injection. Don't manually add `<|im_start|>` etc. to message content.

5. **Tokenizer mismatch**: Always load tokenizer and model from the same
   checkpoint. Mismatched tokenizers produce wrong token IDs.
