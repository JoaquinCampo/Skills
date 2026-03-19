# Pydantic v2: Advanced Features

> TypeAdapter, custom types, generics, settings, dataclasses, discriminated unions, aliases, JSON Schema

## Table of Contents

1. [TypeAdapter](#1-typeadapter)
2. [Custom Types](#2-custom-types)
3. [Generic Models](#3-generic-models)
4. [Dynamic Model Creation](#4-dynamic-model-creation)
5. [Pydantic Settings](#5-pydantic-settings)
6. [Discriminated Unions](#6-discriminated-unions)
7. [Aliases](#7-aliases)
8. [JSON Schema](#8-json-schema)
9. [Dataclasses](#9-dataclasses)
10. [Private Attributes](#10-private-attributes)
11. [Strict Mode](#11-strict-mode)
12. [RootModel](#12-rootmodel)

---

## 1. TypeAdapter

Validate and serialize arbitrary types without a BaseModel.

```python
from pydantic import TypeAdapter

# Simple types
int_adapter = TypeAdapter(int)
result = int_adapter.validate_python('42')      # 42
result = int_adapter.validate_json(b'"hello"')  # for str adapter

# Complex types
list_adapter = TypeAdapter(list[int])
result = list_adapter.validate_python(['1', '2'])  # [1, 2]
json_bytes = list_adapter.dump_json([1, 2, 3])     # b'[1,2,3]'
schema = list_adapter.json_schema()

# With Annotated
from typing import Annotated
from pydantic import Field

adapter = TypeAdapter(Annotated[list[int], Field(min_length=1)])

# With config
from pydantic import ConfigDict
adapter = TypeAdapter(list[str], config=ConfigDict(strict=True))

# Key methods
adapter.validate_python(data)           # validate Python objects
adapter.validate_json(json_str_or_bytes)  # validate JSON
adapter.validate_strings('hello')       # validate from string repr (input must be str)
adapter.dump_python(data)               # serialize to Python
adapter.dump_python(data, mode='json')  # JSON-compatible Python
adapter.dump_json(data)                 # serialize to JSON bytes
adapter.json_schema()                   # generate JSON Schema
```

Replaces v1's `parse_obj_as()` and `schema_of()`.

---

## 2. Custom Types

### Simple approach: Annotated with validators (preferred)

```python
from typing import Annotated
from pydantic import AfterValidator

def _upper(v: str) -> str:
    return v.upper()

UpperString = Annotated[str, AfterValidator(_upper)]
```

### Full custom type: __get_pydantic_core_schema__

```python
from typing import Any
from pydantic import BaseModel, GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema

class MyCustomType:
    def __init__(self, value: str):
        self.value = value

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        return core_schema.no_info_plain_validator_function(
            cls._validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda v: v.value,
                info_arg=False,
            ),
        )

    @classmethod
    def _validate(cls, v: Any) -> 'MyCustomType':
        if isinstance(v, cls):
            return v
        if isinstance(v, str):
            return cls(v)
        raise ValueError(f'Cannot create from {type(v)}')

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        return {"type": "string", "description": "My custom type"}
```

V1 used `__get_validators__` and `__modify_schema__` — both REMOVED.

---

## 3. Generic Models

```python
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar('T')

# V2: Just use BaseModel + Generic[T] directly
# V1's GenericModel is REMOVED
class Response(BaseModel, Generic[T]):
    data: T
    error: Optional[str] = None
    count: int = 0

# Parametrize
UserResponse = Response[UserData]
resp = UserResponse(data={"name": "Alice"}, count=1)

# Nested generics
class Envelope(BaseModel, Generic[T]):
    payload: T
    metadata: dict[str, Any] = {}

nested = Envelope[Response[str]](payload={"data": "hello"})

# Bounded generics
BoundT = TypeVar('BoundT', bound=BaseModel)

class Container(BaseModel, Generic[BoundT]):
    item: BoundT
```

---

## 4. Dynamic Model Creation

```python
from pydantic import BaseModel, Field, ConfigDict, create_model, field_validator

# Basic
DynamicModel = create_model(
    'DynamicModel',
    name=(str, ...),           # (type, default) — ... means required
    age=(int, 25),             # with default
    email=(str, Field(default="n/a", description="Email")),
)

# With base class
class Base(BaseModel):
    name: str

Extended = create_model('Extended', __base__=Base, age=(int, ...))

# With config
Strict = create_model('Strict', __config__=ConfigDict(strict=True), value=(int, ...))

# From dict
fields = {"host": (str, "localhost"), "port": (int, 8080)}
Config = create_model("Config", **fields)
```

---

## 5. Pydantic Settings

Moved to separate package: `pip install pydantic-settings`

```python
# V1: from pydantic import BaseSettings         # WRONG
# V2: from pydantic_settings import BaseSettings  # CORRECT
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MY_APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        secrets_dir="/run/secrets",
    )

    db_host: str = "localhost"
    db_port: int = 5432
    debug: bool = False
    redis_url: str = Field(
        default="redis://localhost:6379",
        validation_alias=AliasChoices("REDIS_URL", "REDIS_DSN"),
    )
```

V1 used inner `class Config:` — V2 uses `SettingsConfigDict(...)`.

### Custom sources priority

Default: init_settings > env > dotenv > secrets. Override with `settings_customise_sources`.

### Additional sources

`JsonConfigSettingsSource`, `TomlConfigSettingsSource`, `YamlConfigSettingsSource`, `PyprojectTomlConfigSettingsSource`, CLI source.

---

## 6. Discriminated Unions

### Method 1: Literal field discriminator

```python
from typing import Literal
from pydantic import BaseModel, Field

class Cat(BaseModel):
    pet_type: Literal['cat']
    meows: int

class Dog(BaseModel):
    pet_type: Literal['dog']
    barks: float

class Home(BaseModel):
    pet: Cat | Dog = Field(discriminator='pet_type')
```

### Method 2: Annotated + Discriminator

```python
from typing import Annotated, Union
from pydantic import Discriminator

Shape = Annotated[Circle | Rectangle, Discriminator('shape')]
```

### Method 3: Callable discriminator (most flexible)

```python
from pydantic import Discriminator, Tag

def get_type(v: Any) -> str:
    if isinstance(v, dict):
        if 'meows' in v: return 'cat'
        if 'barks' in v: return 'dog'
    return 'cat'

TaggedPet = Annotated[
    Annotated[Cat, Tag('cat')] | Annotated[Dog, Tag('dog')],
    Discriminator(get_type),
]
```

---

## 7. Aliases

### Three distinct alias types

```python
from pydantic import BaseModel, Field, ConfigDict

class User(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    # alias: used for BOTH validation and serialization
    name: str = Field(alias='userName')

    # validation_alias: ONLY for input (parsing)
    email: str = Field(validation_alias='email_address')

    # serialization_alias: ONLY for output (dumping)
    age: int = Field(serialization_alias='user_age')
```

### AliasPath — nested data access

```python
from pydantic import AliasPath

# Expects: {"user": {"info": {"name": "Alice"}}}
name: str = Field(validation_alias=AliasPath('user', 'info', 'name'))

# List index: {"tags": ["first", "second"]}
first_tag: str = Field(validation_alias=AliasPath('tags', 0))
```

### AliasChoices — multiple options

```python
from pydantic import AliasChoices

email: str = Field(
    validation_alias=AliasChoices('email', 'email_address', AliasPath('contact', 'email'))
)
```

### AliasGenerator — model-wide

```python
from pydantic import AliasGenerator, ConfigDict
from pydantic.alias_generators import to_camel, to_snake, to_pascal

class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    first_name: str  # accepts "firstName" or "first_name"
    last_name: str

# Advanced: separate validation/serialization aliases
class DualModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            validation_alias=to_camel,
            serialization_alias=to_pascal,
        ),
        populate_by_name=True,
    )
```

---

## 8. JSON Schema

### Generation

```python
schema = MyModel.model_json_schema()  # replaces .schema()
schema = MyModel.model_json_schema(mode='serialization')  # serialization schema

# For non-model types
from pydantic import TypeAdapter
schema = TypeAdapter(list[int]).json_schema()
```

### Field-level customization

```python
from pydantic import Field, WithJsonSchema

name: str = Field(json_schema_extra={'examples': ['John'], 'x-custom': True})
custom: Annotated[dict, WithJsonSchema({'type': 'object', 'description': 'Arbitrary'})]
```

### Model-level customization

```python
model_config = ConfigDict(
    json_schema_extra={'examples': [{'name': 'test'}]},
)

# Or callable
model_config = ConfigDict(
    json_schema_extra=lambda schema: schema.pop('title', None),
)
```

### Custom schema generator

```python
from pydantic.json_schema import GenerateJsonSchema

class MySchema(GenerateJsonSchema):
    def generate(self, schema, mode='validation'):
        result = super().generate(schema, mode=mode)
        result['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
        return result

schema = MyModel.model_json_schema(schema_generator=MySchema)
```

---

## 9. Dataclasses

```python
from pydantic.dataclasses import dataclass
from pydantic import ConfigDict, Field

@dataclass(config=ConfigDict(strict=True, frozen=True))
class User:
    age: int
    name: str = Field(min_length=1, default='unknown')

# Key differences from BaseModel:
# - NO model_dump(), model_dump_json(), model_json_schema()
# - Use TypeAdapter for serialization:
from pydantic import TypeAdapter
adapter = TypeAdapter(User)
schema = adapter.json_schema()
json_bytes = adapter.dump_json(User(age=30, name='John'))

# Supports __post_init__
@dataclass
class Processed:
    name: str
    slug: str = ''

    def __post_init__(self):
        if not self.slug:
            self.slug = self.name.lower().replace(' ', '-')

# Stdlib dataclasses work too (validated via TypeAdapter)
import dataclasses
@dataclasses.dataclass
class StdUser:
    __pydantic_config__ = ConfigDict(strict=False)
    name: str
    age: int

adapter = TypeAdapter(StdUser)
user = adapter.validate_python({"name": "Alice", "age": 30})  # coerces dict -> StdUser
```

---

## 10. Private Attributes

```python
from datetime import datetime
from pydantic import BaseModel, PrivateAttr

class Model(BaseModel):
    _created_at: datetime = PrivateAttr(default_factory=datetime.now)
    _secret: int = PrivateAttr(default=42)
    name: str
```

- Names MUST start with underscore
- NOT in schema, `model_dump()`, or `model_dump_json()`
- NOT set during `__init__` — set via `default` or `default_factory`
- Dunder names (`__attr__`) are completely ignored

---

## 11. Strict Mode

Three levels:

```python
# Per-model
model_config = ConfigDict(strict=True)

# Per-field
from pydantic import Field
from pydantic.types import Strict
count: Annotated[int, Strict()]  # or StrictInt, or Field(strict=True)

# Per-call
MyModel.model_validate(data, strict=True)
TypeAdapter(int).validate_python('123', strict=True)  # raises
```

In strict mode: `"123"` will NOT coerce to `int`. Only exact types accepted.

---

## 12. RootModel

Replaces v1's `__root__`.

```python
from pydantic import RootModel

class Pets(RootModel[list[str]]):
    pass

pets = Pets(['dog', 'cat'])
pets.root                    # ['dog', 'cat']
pets.model_dump()            # ['dog', 'cat']
Pets.model_validate(['a'])   # works

# Dict root
class Lookup(RootModel[dict[str, int]]):
    pass

# Inherits all BaseModel methods
```
