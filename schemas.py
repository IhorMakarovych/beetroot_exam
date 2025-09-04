from pydantic import BaseModel
from models import Ingredient, Step, Recipe
from typing import List

class RecipeCreateForm(BaseModel):
    title: str
    type: str
    min_time: int = 0
    max_time: int = 0
    ingredients: str  # lines like 'Tomato: 200g'
    steps: str  # textarea with newlines

    def to_model(self, author_id: int):
        r = Recipe(title=self.title, type=self.type, min_time=self.min_time, max_time=self.max_time, author_id=author_id)
        # parse ingredients and steps
        r.ingredients = []
        r.steps = []
        for line in self.ingredients.splitlines():
            if not line.strip(): continue
            parts = line.split(':',1)
            name = parts[0].strip()
            qty = parts[1].strip() if len(parts)>1 else ''
            r.ingredients.append(Ingredient(name=name, qty=qty))
        for idx, line in enumerate(self.steps.splitlines(), start=1):
            if not line.strip(): continue
            r.steps.append(Step(order=idx, description=line.strip()))
        return r
