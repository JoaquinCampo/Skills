# Pydantic v2: Validators, Serializers & Computed Fields

> Complete reference for all validation and serialization patterns.

## Table of Contents

1. [Field Validators](#1-field-validators)
2. [Model Validators](#2-model-validators)
3. [@validate_call](#3-validate_call)
4. [Serialization](#4-serialization)
5. [Computed Fields](#5-computed-fields)
6. [Raising Errors](#6-raising-errors)

---

## 1. Field Validators

### Four Validator Modes

| Mode     | Runs When                              | Input Type           | Use Case                     |
|----------|----------------------------------------|----------------------|------------------------------|
| `after`  | After Pydantic's internal validation   | Validated Python type| Type-safe checks (default)   |
| `before` | Before Pydantic's internal validation  | `Any` (raw input)    | Coercion, pre-processing     |
| `plain`  | Replaces Pydantic's validation entirely| `Any` (raw input)    | Full custom validation       |
| `wrap`   | Wraps Pydantic's validation            | `Any` + handler      | Conditional delegation       |

### Annotated Pattern (preferred for reusable types)

```python
from typing import Annotated, Any
from pydantic import BaseModel, AfterValidator, BeforeValidator, PlainValidator, WrapValidator

def is_even(v: int) -> int:
    if v % 2 == 1:
        raise ValueError(f'{v} is not even')
    return v

def coerce_to_int(v: Any) -> Any:
    if isinstance(v, str) and v.isdigit():
        return int(v)
    return v

EvenInt = Annotated[int, AfterValidator(is_even)]
FlexibleInt = Annotated[int, BeforeValidator(coerce_to_int)]

# Chaining: validators compose left-to-right in Annotated
TrimmedUpper = Annotated[
    str,
    BeforeValidator(lambda v: v.strip() if isinstance(v, str) else v),
    AfterValidator(lambda v: v.upper()),
]
```

### Decorator Pattern (@field_validator)

```python
from pydantic import BaseModel, field_validator, ValidationInfo

class Model(BaseModel):
    name: str
    age: int

    # MUST be @classmethod. MUST return value.
    @field_validator('name')
    @classmethod
    def check_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('empty')
        return v.strip()

    # Multiple fields
    @field_validator('name', 'age', mode='before')
    @classmethod
    def coerce(cls, v: Any) -> Any:
        if isinstance(v, bytes):
            return v.decode()
        return v

    # All fields
    @field_validator('*', mode='before')
    @classmethod
    def no_none(cls, v: Any) -> Any:
        if v is None:
            raise ValueError('None not allowed')
        return v

    # Accessing other fields via ValidationInfo
    @field_validator('age')
    @classmethod
    def check_age(cls, v: int, info: ValidationInfo) -> int:
        # info.data has previously validated fields (definition order)
        if 'name' in info.data:
            pass  # can access info.data['name']
        return v
```

### Wrap Validator

```python
from pydantic import WrapValidator, ValidatorFunctionWrapHandler

def wrap_val(v: Any, handler: ValidatorFunctionWrapHandler) -> int:
    if isinstance(v, str) and v.startswith('#'):
        v = int(v[1:], 16)  # hex
    return handler(v)  # delegate to Pydantic

HexOrInt = Annotated[int, WrapValidator(wrap_val)]
```

---

## 2. Model Validators

### mode='after' — Instance Method

```python
from typing import Self
from pydantic import BaseModel, model_validator

class UserModel(BaseModel):
    password: str
    password_repeat: str

    @model_validator(mode='after')
    def check_passwords(self) -> Self:
        if self.password != self.password_repeat:
            raise ValueError('Passwords do not match')
        return self  # MUST return self
```

NOT a classmethod. Receives fully validated model instance.

### mode='before' — Classmethod

```python
from typing import Any
from pydantic import BaseModel, model_validator

class UserModel(BaseModel):
    username: str

    @model_validator(mode='before')
    @classmethod
    def preprocess(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if 'card_number' in data:
                raise ValueError("card_number should not be included")
        return data  # MUST return data
```

Data is `Any` (usually dict). MUST be `@classmethod`. Always check `isinstance(data, dict)`.

### mode='wrap' — Classmethod with Handler

```python
from typing import Any, Self
from pydantic import BaseModel, ModelWrapValidatorHandler, model_validator

class UserModel(BaseModel):
    username: str

    @model_validator(mode='wrap')
    @classmethod
    def log_validation(cls, data: Any, handler: ModelWrapValidatorHandler[Self]) -> Self:
        try:
            return handler(data)
        except ValidationError:
            logging.error('Validation failed for %s', data)
            raise
```

---

## 3. @validate_call

Validates function arguments (and optionally return values).

```python
from pydantic import validate_call, ConfigDict

@validate_call
def repeat(s: str, count: int, *, separator: bytes = b'') -> bytes:
    return separator.join(s.encode() for _ in range(count))

repeat('hello', '3')  # '3' coerced to int

# With strict mode and return validation
@validate_call(config=ConfigDict(strict=True), validate_return=True)
def add(a: int, b: int) -> int:
    return a + b

# Using Field() for parameter constraints
from typing import Annotated
from pydantic import Field

@validate_call
def schedule(
    event: Annotated[str, Field(min_length=1, max_length=100)],
    priority: Annotated[int, Field(ge=1, le=5)] = 3,
) -> dict:
    return {"event": event, "priority": priority}
```

Renamed from `@validate_arguments` (v1).

---

## 4. Serialization

### model_dump() Parameters

```python
model.model_dump(
    mode='python',          # 'python' (default) or 'json' (JSON-compatible types)
    include={'name', 'age'},
    exclude={'password'},
    by_alias=True,
    exclude_unset=True,     # Only fields explicitly set
    exclude_defaults=True,  # Fields equal to their default
    exclude_none=True,      # Fields with None value
    serialize_as_any=True,  # Include subclass fields (v1 behavior)
    context={'key': 'val'}, # Pass context to serializers
)
```

### model_dump_json() Parameters

```python
model.model_dump_json(
    indent=2,
    # Same options as model_dump: by_alias, exclude_unset, etc.
)
```

### Field Serializers

#### Decorator pattern

```python
from pydantic import BaseModel, field_serializer

class Model(BaseModel):
    number: int
    joined: datetime

    # Plain mode (default) — replaces Pydantic's serialization
    @field_serializer('number')
    def double_number(self, v: int, _info) -> int:
        return v * 2

    # Multiple fields
    @field_serializer('number', 'joined', mode='plain')
    def ser_all(self, v: Any, _info) -> str:
        return str(v)

    # Wrap mode — modify Pydantic's default
    @field_serializer('joined', mode='wrap')
    def wrap_joined(self, v: datetime, handler, _info) -> str:
        result = handler(v)
        return f"date:{result}"
```

Note: `@field_serializer` is an instance method (or static/classmethod), NOT like `@field_validator`.

#### Annotated pattern

```python
from pydantic import PlainSerializer, WrapSerializer

DoubledInt = Annotated[int, PlainSerializer(lambda v: v * 2)]

from pydantic import SerializerFunctionWrapHandler

def wrap_ser(v: Any, handler: SerializerFunctionWrapHandler) -> Any:
    result = handler(v)
    return f"wrapped_{result}"

WrappedStr = Annotated[str, WrapSerializer(wrap_ser)]
```

#### Serialization context

```python
from pydantic import FieldSerializationInfo

@field_serializer('text')
@classmethod
def filter_text(cls, v: str, info: FieldSerializationInfo) -> str:
    if isinstance(info.context, dict):
        stopwords = info.context.get('stopwords', set())
        return ' '.join(w for w in v.split() if w.lower() not in stopwords)
    return v

model.model_dump(context={'stopwords': ['the', 'is']})
```

### Model Serializers

```python
from pydantic import BaseModel, SerializerFunctionWrapHandler, model_serializer

# Plain — full control
class User(BaseModel):
    username: str
    password: str

    @model_serializer(mode='plain')
    def serialize(self) -> str:
        return f'{self.username}:***'

# Wrap — modify default dict output
class User2(BaseModel):
    username: str

    @model_serializer(mode='wrap')
    def serialize(self, handler: SerializerFunctionWrapHandler) -> dict:
        d = handler(self)
        d['_type'] = 'User'
        return d
```

---

## 5. Computed Fields

```python
from functools import cached_property
from pydantic import BaseModel, ConfigDict, computed_field

class Box(BaseModel):
    width: float
    height: float
    depth: float

    @computed_field
    @property                        # MUST use @property or @cached_property
    def volume(self) -> float:       # Return type REQUIRED
        return self.width * self.height * self.depth

b = Box(width=1, height=2, depth=3)
b.volume                             # 6.0
b.model_dump()                       # includes 'volume': 6.0
b.model_dump_json()                  # includes volume
Box.model_json_schema(mode='serialization')  # volume in schema (serialization mode only)
```

Key rules:
- `@computed_field` MUST stack on `@property` or `@cached_property`
- Return type annotation is REQUIRED
- Included in `model_dump()`, `model_dump_json()`, and JSON Schema
- Pydantic does NOT validate the computed value
- Cannot use `Field()` — use `computed_field(alias=..., repr=False)` etc.
- Exclude with `model_dump(exclude_computed_fields=True)` (v2.12+)

---

## 6. Raising Errors

Three valid exception types inside validators:

```python
# 1. ValueError — most common
raise ValueError('Name cannot be empty')

# 2. AssertionError — via assert (skipped with python -O)
assert len(v) > 0, 'empty'

# 3. PydanticCustomError — custom error type/template
from pydantic_core import PydanticCustomError

raise PydanticCustomError(
    'my_error_type',            # machine-readable type
    '{value} is not valid!',    # human template
    {'value': v},               # template context
)
```

Do NOT raise `ValidationError` directly from validators — raise `ValueError` or `PydanticCustomError`.
