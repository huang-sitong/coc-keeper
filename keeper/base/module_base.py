# -*- coding: utf-8 -*-
"""模组/敌人模型共享基类。"""
from pydantic import BaseModel, ConfigDict

class ModuleBaseModel(BaseModel):
    """统一允许 snake_case 字段名 + camelCase JSON alias。"""

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
