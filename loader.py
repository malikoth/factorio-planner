import re
from collections import deque


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


recipes = load_recipes()
products = [line.strip() for line in open("mall_products.txt") if not line.startswith("#")]
exclusive_products = {line.strip() for line in open("exclusive_products.txt") if not line.startswith("#")}
intermediates = {line.strip() for line in open("intermediates.txt") if not line.startswith("#")}
