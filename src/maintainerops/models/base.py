"""Lightweight compatibility layer for BaseModel supporting both Pydantic and Pure-Python dataclasses."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, get_args, get_origin


try:
    from pydantic import BaseModel as _PydanticBaseModel
    from pydantic import Field as _PydanticField

    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False


if HAS_PYDANTIC:
    class BaseModel(_PydanticBaseModel):
        pass

    def Field(*args, **kwargs):
        return _PydanticField(*args, **kwargs)

else:
    class BaseModel:
        def __init__(self, **data: Any):
            cls_annotations = getattr(self.__class__, "__annotations__", {})
            for key, val in data.items():
                target_type = cls_annotations.get(key)
                # Handle nested BaseModel
                if isinstance(val, dict) and isinstance(target_type, type) and issubclass(target_type, BaseModel):
                    val = target_type(**val)
                # Handle List[BaseModel]
                elif isinstance(val, list) and target_type is not None:
                    origin = get_origin(target_type)
                    args = get_args(target_type)
                    if origin is list and args and isinstance(args[0], type) and issubclass(args[0], BaseModel):
                        child_cls = args[0]
                        val = [child_cls(**item) if isinstance(item, dict) else item for item in val]
                setattr(self, key, val)

            for key, default in self.__class__.__dict__.items():
                if not key.startswith("_") and key not in data and not callable(default):
                    setattr(self, key, default)

        def model_dump(self, mode: str = "python") -> Dict[str, Any]:
            result = {}
            for k, v in self.__dict__.items():
                if k.startswith("_"):
                    continue
                if isinstance(v, BaseModel):
                    result[k] = v.model_dump(mode=mode)
                elif isinstance(v, list):
                    result[k] = [item.model_dump(mode=mode) if isinstance(item, BaseModel) else item for item in v]
                elif hasattr(v, "isoformat"):
                    result[k] = v.isoformat()
                elif hasattr(v, "value"):
                    result[k] = v.value
                else:
                    result[k] = v
            return result

        def __repr__(self) -> str:
            attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items() if not k.startswith("_"))
            return f"{self.__class__.__name__}({attrs})"

    def Field(default=None, default_factory=None, **kwargs):
        if default_factory is not None:
            return default_factory()
        return default
