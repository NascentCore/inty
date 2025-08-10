# Write a minimal test to show how to initialize a pydantic submodel from a basemodel object

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