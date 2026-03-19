# Pydantic V1 to V2 Complete Migration Reference

> Pydantic v2.12.5 — Compiled from official docs

## Table of Contents

1. [BaseModel Method Renames](#1-basemodel-method-renames)
2. [Config Class to ConfigDict](#2-config-class-to-configdict)
3. [Validators: @validator to @field_validator](#3-validators)
4. [Model Validators: @root_validator to @model_validator](#4-model-validators)
5. [Field() Changes](#5-field-changes)
6. [Removed Features](#6-removed-features)
7. [Behavioral Changes](#7-behavioral-changes)
8. [Import Path Changes](#8-import-path-changes)
9. [Common LLM Mistakes Catalogue](#9-common-llm-mistakes)

---

## 1. BaseModel Method Renames

| Pydantic V1                  | Pydantic V2                        |
|------------------------------|------------------------------------|
| `__fields__`                 | `model_fields`                     |
| `__private_attributes__`     | `__pydantic_private__`             |
| `__validators__`             | `__pydantic_validator__`           |
| `construct()`                | `model_construct()`                |
| `copy()`                     | `model_copy()`                     |
| `dict()`                     | `model_dump()`                     |
| `json()`                     | `model_dump_json()`                |
| `parse_obj()`                | `model_validate()`                 |
| `parse_raw()`                | `model_validate_json()`            |
| `parse_file()`               | *Removed* — load file then `model_validate()` |
| `from_orm()`                 | `model_validate()` with `from_attributes=True` in config |
| `schema()`                   | `model_json_schema()`              |
| `schema_json()`              | `json.dumps(model_json_schema())`  |
| `validate()`                 | `model_validate()`                 |
| `update_forward_refs()`      | `model_rebuild()`                  |

### copy() -> model_copy() parameter changes

```python
# V1
obj.copy(update={"field": "value"}, include={"field"}, exclude={"other"})

# V2 — include/exclude removed from model_copy
obj.model_copy(update={"field": "value"})
# For filtering: use model_dump(include=..., exclude=...) instead
```

### from_orm() -> model_validate() with from_attributes

```python
# V1
class MyModel(BaseModel):
    class Config:
        orm_mode = True

obj = MyModel.from_orm(some_orm_instance)

# V2
from pydantic import BaseModel, ConfigDict

class MyModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

obj = MyModel.model_validate(some_orm_instance)
```

---

## 2. Config Class to ConfigDict

The inner `class Config:` is deprecated. Use `model_config = ConfigDict(...)`.

```python
# V1 (WRONG)
class MyModel(BaseModel):
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        schema_extra = {"example": {"name": "test"}}

# V2 (CORRECT)
from pydantic import BaseModel, ConfigDict

class MyModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={"example": {"name": "test"}},
    )
```

### Config Settings Renamed

| V1                                  | V2                              |
|-------------------------------------|---------------------------------|
| `orm_mode`                          | `from_attributes`               |
| `allow_population_by_field_name`    | `populate_by_name`              |
| `schema_extra`                      | `json_schema_extra`             |
| `validate_all`                      | `validate_default`              |
| `anystr_lower`                      | `str_to_lower`                  |
| `anystr_upper`                      | `str_to_upper`                  |
| `anystr_strip_whitespace`           | `str_strip_whitespace`          |
| `max_anystr_length`                 | `str_max_length`                |
| `min_anystr_length`                 | `str_min_length`                |
| `keep_untouched`                    | `ignored_types`                 |

### Config Settings REMOVED

| Removed                   | Replacement                                     |
|---------------------------|-------------------------------------------------|
| `allow_mutation`          | `frozen=True` (inverted logic)                  |
| `error_msg_templates`     | Use `PydanticCustomError` in validators          |
| `fields`                  | Use `Annotated` with `Field()` on each field     |
| `getter_dict`             | Removed                                          |
| `smart_union`             | V2 default `union_mode` is already `'smart'`     |
| `underscore_attrs_are_private` | V2 always treats `_` attrs as private       |
| `json_loads` / `json_dumps`   | Use custom serializers                       |
| `copy_on_model_validation`    | Removed                                      |
| `post_init_call`              | Removed                                      |

### Complete ConfigDict Options (v2.12.5)

```python
from pydantic import ConfigDict

model_config = ConfigDict(
    # String processing
    str_strip_whitespace=False,
    str_to_lower=False,
    str_to_upper=False,
    str_min_length=0,
    str_max_length=None,

    # Behavior
    strict=False,              # Disable all type coercion
    frozen=False,              # Make instances immutable
    extra='ignore',            # 'ignore' | 'allow' | 'forbid'
    validate_assignment=False, # Re-validate on attribute assignment
    validate_default=False,    # Validate default values
    revalidate_instances='never',  # 'never' | 'always' | 'subclass-instances'

    # Aliases
    populate_by_name=False,    # Allow field name when alias is set
    validate_by_name=False,    # v2.11+: replaces populate_by_name
    validate_by_alias=True,    # v2.11+
    serialize_by_alias=False,  # v2.11+
    alias_generator=None,      # Callable or AliasGenerator
    loc_by_alias=True,         # Use alias in error locations

    # ORM / attributes
    from_attributes=False,     # Create from ORM objects

    # Types
    arbitrary_types_allowed=False,
    use_enum_values=False,
    coerce_numbers_to_str=False,

    # JSON
    json_schema_extra=None,
    json_encoders=None,        # DEPRECATED — use @field_serializer
    ser_json_timedelta='iso8601',
    ser_json_bytes='utf8',
    ser_json_inf_nan='null',

    # Regex
    regex_engine='rust-regex',  # or 'python-re' for lookaheads

    # Other
    protected_namespaces=('model_',),
    ignored_types=(),
    hide_input_in_errors=False,
    defer_build=False,
    use_attribute_docstrings=False,
)
```

---

## 3. Validators

### @validator -> @field_validator

```python
# V1 (WRONG)
from pydantic import validator

class MyModel(BaseModel):
    name: str

    @validator("name")
    def check_name(cls, v):
        return v.strip()

    @validator("name", pre=True)
    def coerce(cls, v):
        return str(v)

    @validator("items", each_item=True)
    def check_item(cls, v):
        return v

# V2 (CORRECT)
from pydantic import field_validator

class MyModel(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def check_name(cls, v: str) -> str:
        return v.strip()

    @field_validator("name", mode="before")
    @classmethod
    def coerce(cls, v: Any) -> Any:
        return str(v)

    # each_item removed — use Annotated on inner type
    items: list[Annotated[str, AfterValidator(check_item_fn)]]
```

### Critical Differences

1. **`@classmethod` is REQUIRED** — v1 inferred it, v2 does not.
2. **`pre=True`** -> **`mode='before'`**. Default is `'after'` (v1's `pre=False`).
3. **`each_item=True`** -> Use `Annotated` on inner type with `AfterValidator`.
4. **`always=True`** -> Use `validate_default=True` in `Field()` or `model_config`.
5. **`values` dict parameter** -> Use `info: ValidationInfo` with `info.data`.
6. **The `field` parameter** (FieldInfo) is gone.
7. **Return value is MANDATORY** — forgetting `return v` silently sets field to `None`.

### Accessing Previously Validated Fields

```python
from pydantic import ValidationInfo, field_validator

class Model(BaseModel):
    password: str
    confirm: str

    @field_validator('confirm')
    @classmethod
    def match(cls, v: str, info: ValidationInfo) -> str:
        if 'password' in info.data and v != info.data['password']:
            raise ValueError('mismatch')
        return v
```

`info.data` only contains fields validated **before** the current one (definition order).

---

## 4. Model Validators

### @root_validator -> @model_validator

```python
# V1 (WRONG)
from pydantic import root_validator

class MyModel(BaseModel):
    @root_validator
    def check(cls, values):
        return values

    @root_validator(pre=True)
    def pre_check(cls, values):
        return values

# V2 (CORRECT)
from pydantic import model_validator
from typing import Self

class MyModel(BaseModel):
    # mode='after': instance method (NOT classmethod!)
    @model_validator(mode='after')
    def check(self) -> Self:
        # access self.field_name directly
        return self  # MUST return self

    # mode='before': classmethod, receives raw data
    @model_validator(mode='before')
    @classmethod
    def pre_check(cls, data: Any) -> Any:
        if isinstance(data, dict):
            pass  # transform
        return data

    # mode='wrap': classmethod with handler
    @model_validator(mode='wrap')
    @classmethod
    def wrap_check(cls, data: Any, handler) -> Self:
        result = handler(data)  # delegate to Pydantic
        return result
```

### Critical Differences

1. **`mode='after'`** receives `self` (instance method), NOT `cls`.
2. **`mode='before'`** receives `cls, data: Any` (classmethod). Data is usually dict but check.
3. **No `values` dict** in after mode — access fields as `self.field_name`.
4. After mode MUST return `self`. Before mode MUST return `data`.

---

## 5. Field() Changes

### Removed Parameters

| V1 Parameter       | V2 Replacement                     |
|--------------------|------------------------------------|
| `const=True`       | Use `Literal[value]` type          |
| `regex="..."`      | `pattern="..."`                    |
| `min_items=N`      | `min_length=N`                     |
| `max_items=N`      | `max_length=N`                     |
| `unique_items=True` | Use `set` or `frozenset` type     |
| `allow_mutation=False` | `frozen=True`                  |
| `final=True`       | Use `typing.Final` type            |

### Arbitrary kwargs removed

```python
# V1 — arbitrary kwargs went into JSON schema
name: str = Field(..., example="John")

# V2 — use json_schema_extra
name: str = Field(..., json_schema_extra={"example": "John"})
```

---

## 6. Removed Features

| Feature                     | Replacement                              |
|-----------------------------|------------------------------------------|
| `GenericModel`              | `BaseModel` + `Generic[T]` directly      |
| `__root__`                  | `RootModel[T]`                           |
| `__get_validators__`        | `__get_pydantic_core_schema__`           |
| `__modify_schema__`         | `__get_pydantic_json_schema__`           |
| `parse_file()`              | Load file yourself, then `model_validate()` |
| `validate_arguments`        | `validate_call`                          |
| `parse_obj_as(T, data)`     | `TypeAdapter(T).validate_python(data)`   |
| `schema_of(T)`              | `TypeAdapter(T).json_schema()`           |
| `json_encoders` in Config   | Use `@field_serializer`                  |

---

## 7. Behavioral Changes

### Optional[X] no longer implies default=None

```python
# V1: Optional[str] implicitly set default=None
# V2: Optional[str] accepts str|None but is STILL REQUIRED
name: str | None      # REQUIRED, no default
name: str | None = None  # has default
```

### Subclass serialization

V1 serialized all subclass fields. V2 only serializes fields of the declared type.
Use `serialize_as_any=True` or `model_dump(serialize_as_any=True)` for v1 behavior.

### Models no longer equal dicts

```python
# V1: MyModel(x=1) == {"x": 1}  -> True
# V2: MyModel(x=1) == {"x": 1}  -> False
```

### URL types are no longer strings

```python
url = HttpUrl('https://example.com')
# url + '/path'    # WRONG — not a str
str(url) + '/path'  # CORRECT
```

### Regex engine

V2 uses Rust `regex` crate (no lookaheads/backreferences). For Python regex:
```python
model_config = ConfigDict(regex_engine='python-re')
```

### json_encoders deprecated

```python
# V1
class Config:
    json_encoders = {datetime: lambda v: v.isoformat()}

# V2 — use @field_serializer
@field_serializer('dt')
def ser_dt(self, v: datetime, _info) -> str:
    return v.isoformat()
```

---

## 8. Import Path Changes

| V1 Import                              | V2 Import                                    |
|-----------------------------------------|----------------------------------------------|
| `from pydantic import validator`        | `from pydantic import field_validator`        |
| `from pydantic import root_validator`   | `from pydantic import model_validator`        |
| `from pydantic.generics import GenericModel` | Removed — use `BaseModel` + `Generic`   |
| `from pydantic import validate_arguments` | `from pydantic import validate_call`       |
| `from pydantic.tools import parse_obj_as` | `TypeAdapter(T).validate_python(...)`      |
| `from pydantic.tools import schema_of`  | `TypeAdapter(T).json_schema()`               |
| `from pydantic import BaseSettings`     | `from pydantic_settings import BaseSettings`  |

### V1 compatibility layer

```python
# Temporary bridge during migration:
from pydantic.v1 import BaseModel  # V1 BaseModel within V2 package
```

---

## 9. Common LLM Mistakes

1. Using `@validator` instead of `@field_validator`
2. Forgetting `@classmethod` on `@field_validator`
3. Using `pre=True` instead of `mode='before'`
4. Using `each_item=True` — removed; use `Annotated[T, AfterValidator(...)]`
5. Using `values` dict in field validators — use `info: ValidationInfo` + `info.data`
6. Using inner `class Config:` instead of `model_config = ConfigDict(...)`
7. Using `orm_mode=True` instead of `from_attributes=True`
8. Using `.dict()` / `.json()` instead of `.model_dump()` / `.model_dump_json()`
9. Using `.parse_obj()` / `.parse_raw()` instead of `.model_validate()` / `.model_validate_json()`
10. Using `.from_orm()` instead of `.model_validate()`
11. Using `schema_extra` instead of `json_schema_extra`
12. Using `Field(regex=...)` instead of `Field(pattern=...)`
13. Using `Field(const=True)` instead of `Literal[value]` type
14. Using `Field(min_items=...)` instead of `Field(min_length=...)`
15. Using `GenericModel` — removed; use `BaseModel, Generic[T]`
16. Using `__root__` instead of `RootModel`
17. Using `__get_validators__` instead of `__get_pydantic_core_schema__`
18. Assuming `Optional[X]` gives a default of `None` — V2 requires explicit `= None`
19. Using `@root_validator` instead of `@model_validator`
20. Using `self` in `mode='before'` model_validator — should be `cls` + `@classmethod`
21. Using `cls` in `mode='after'` model_validator — should be `self` (instance method)
22. Forgetting to return the value from validators
23. Using `allow_population_by_field_name` instead of `populate_by_name`
24. Using `validate_all` instead of `validate_default`
25. Raising `ValidationError` directly in validators — raise `ValueError` or `PydanticCustomError`
26. Using `json_encoders` in config — use `@field_serializer`
27. Using `update_forward_refs()` instead of `model_rebuild()`
28. Using `construct()` instead of `model_construct()`
