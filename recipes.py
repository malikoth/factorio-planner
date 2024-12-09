import re
from collections import deque
from itertools import chain


def load_recipes():
    RECIPE_NAME = r'"(?P<recipe_name>.*)",'
    ATTRIBUTE = r'^(?P<attribute>\S*) = "?(?P<value>\S*?)"?,?$'

    stack = deque()
    recipes = {}
    ingredient = {}
    recipe_name = ""
    ingredients = []

    for line in open("recipes.raw"):
        line = line.strip()
        if line == "{":
            stack.append(line)
        elif line.startswith("}"):
            stack.pop()
            if len(stack) == 4:
                ingredients.append(ingredient)
                ingredient = {}
            elif len(stack) == 3:
                recipes[recipe_name] = [i["name"] for i in ingredients if i["type"] != "fluid"]
                ingredients = []

        else:
            if len(stack) == 2:
                recipe_name = re.match(RECIPE_NAME, line).group("recipe_name")
            if len(stack) == 5:
                attribute, value = re.match(ATTRIBUTE, line).groups()
                ingredient[attribute] = value
    return recipes


def get_recipe_ingredients(recipe: str) -> tuple[str]:
    # Exclude these because I'm just going to position one recipe that requires either of these per rowside,
    # right next to the bus so that I don't have to extend a lane specifically for that recipe down the row
    exclude = {"stone", "stone-brick"}

    if recipe not in recipes or recipe in intermediates:
        return_var = {recipe}
    else:
        iterator = (get_recipe_ingredients(ingredient) for ingredient in recipes[recipe])
        return_var = set(chain.from_iterable(iterator))

    return tuple(sorted(return_var - exclude))


recipes = load_recipes()
products = [line.strip() for line in open("mall_products.txt") if not line.startswith("#")]
exclusive_products = {line.strip() for line in open("exclusive_products.txt") if not line.startswith("#")}
intermediates = {line.strip() for line in open("intermediates.txt") if not line.startswith("#")}
