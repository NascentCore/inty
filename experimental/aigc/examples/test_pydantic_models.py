# 编写一个最小测试来展示如何从基本模型对象初始化 pydantic 子模型

import unittest
from pydantic import BaseModel

class MyBaseModel(BaseModel):
    name: str

class MySubModel(MyBaseModel):
    def show(self):
        print(self.name)

def test_submodel_from_basemodel():
    base_model = MyBaseModel(name="test")
    sub_model = MySubModel(**base_model.model_dump())
    sub_model.show()

if __name__ == "__main__":
    unittest.main()