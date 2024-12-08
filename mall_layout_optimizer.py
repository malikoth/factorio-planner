"""Process raw recipe data into an ingestable dictionary.

CAUTION: The following step disables achievements. Do not use on primary savefiles
Dump raw recipe data in-game with the following console command

/c local list = {} for _, recipe in pairs(game.player.force.recipes) do list[#list+1] = {recipe.name,{recipe.ingredients}} end helpers.write_file("recipes.txt", serpent.block(list))
"""

import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from itertools import chain
from typing import ClassVar, Iterable


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


def get_ingredients_key(recipe: str) -> tuple[str]:
    intermediates = [
        "iron-plate",
        "copper-plate",
        "steel-plate",
        "iron-gear-wheel",
        # "copper-cable",
        "stone-brick",
        "electronic-circuit",
        "advanced-circuit",
        "processing-unit",
        "battery",
    ]
    if recipe not in recipes or recipe in intermediates:
        return (recipe,)

    iterator = (get_ingredients_key(ingredient) for ingredient in recipes[recipe])
    return tuple(sorted(set(chain.from_iterable(iterator))))


def populated_list() -> list[str | None]:
    return [None] * 8


@dataclass
class MallRow:
    MAX_LANES: ClassVar[int] = 8

    class Side(Enum):
        TOP = "top"
        BOT = "bottom"

    ingredient_lanes: list[str] = field(default_factory=populated_list)
    recipes_top: list[str] = field(default_factory=list)
    recipes_bot: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.ingredient_lanes) < self.MAX_LANES:
            self.ingredient_lanes += [None] * (self.MAX_LANES - len(self.ingredient_lanes))

    def get_side_range(self, side: Side) -> slice:
        if side == self.Side.TOP:
            return slice(0, 6)
        elif side == self.Side.BOT:
            return slice(2, 8)

    def get_recipes(self, side: Side) -> list[str]:
        if side == self.Side.TOP:
            return self.recipes_top
        elif side == self.Side.BOT:
            return self.recipes_bot

    def add_recipes(self, side: Side, recipes: list[str]) -> None:
        if side == self.Side.TOP:
            self.recipes_top.extend(recipes)
        elif side == self.Side.BOT:
            self.recipes_bot.extend(recipes)

    def get_ingredients(self, side: Side) -> tuple[str]:
        return tuple(self.ingredient_lanes[self.get_side_range(side)])

    def lane_indices(self, side: Side) -> Iterable[int]:
        if side == self.Side.TOP:
            return [2, 3, 4, 5, 0, 1]
        if side == self.Side.BOT:
            return [2, 3, 4, 5, 6, 7]

    def count_available_lanes(self, side: Side) -> int:
        return self.get_ingredients(side).count(None)

    def add_ingredient(self, side: Side, ingredient: str) -> None:
        for lane in self.lane_indices(side):
            if self.ingredient_lanes[lane] is None:
                self.ingredient_lanes[lane] = ingredient
                return
        raise Exception("All ingredient lanes full")

    def __iter__(self):
        for side in self.Side:
            yield (side, self.get_ingredients(side))

    def __str__(self):
        lines = []
        for i in [0, 1]:
            lines.append(self.ingredient_lanes[i] or "----")
        for recipe in sorted(self.recipes_top):
            lines.append(f"    {recipe}")
        for i in [2, 3, 4, 5]:
            lines.append(self.ingredient_lanes[i] or "----")
        for recipe in sorted(self.recipes_bot):
            lines.append(f"    {recipe}")
        for i in [6, 7]:
            lines.append(self.ingredient_lanes[i] or "----")
        return "\n".join(lines)


def find_best_ingredients(row_ingredients: list[str], pending_assignment: set[str]) -> tuple[tuple[str], list[str]]:
    """Find the best ingredient(s) to add to one side of a MallRow

    Also include the list of recipes enabled by the best ingredient(s) in the return
    """
    reduced_ingredients = defaultdict(list)

    for recipe in pending_assignment:
        reduced = tuple(sorted(set(get_ingredients_key(recipe)) - set(row_ingredients)))
        existing_ingredients_used = len(recipes[recipe]) - len(reduced)

        if row_ingredients.count(None) >= len(reduced):
            reduced_ingredients[(existing_ingredients_used, reduced)].append(recipe)

    if not reduced_ingredients:
        return (), []

    # Sort candidate ingredients by:
    #   1. require the fewest new ingredients
    #   2. use the most existing ingredients
    #   3. enable the most number of new recipes
    sorted_ingredients = sorted(
        reduced_ingredients.keys(), key=lambda e: (len(e[1]), -e[0], -len(reduced_ingredients[e]))
    )

    return sorted_ingredients[0], reduced_ingredients[sorted_ingredients[0]]


def sort_ingredients(
    pending_assignment: set[str], rows: list[MallRow]
) -> list[tuple[int, MallRow.Side, tuple[str], list[str]]]:
    """Find candidates for an ingredient to add to a lane on each side of each row"""
    best_by_row = []
    for row_index, row in enumerate(rows):
        for side, row_ingredients in row:
            ingredients, new_recipes = find_best_ingredients(row_ingredients, pending_assignment)
            if not new_recipes:
                continue

            best_by_row.append((row_index, side, ingredients, new_recipes))
    return sorted(best_by_row, key=lambda e: (len(e[2][1]), -e[2][0], -len(e[3])))


def initial_lanes() -> list[MallRow]:
    row1 = MallRow(ingredient_lanes=["iron-plate", None, "iron-gear-wheel", "electronic-circuit"])
    row2 = MallRow(ingredient_lanes=["stone", "stone-brick"])
    return [row1, row2]


def add_ingredients(sorted_ingredients, pending_assignment, rows) -> bool:
    row_index, side, (existing_ingredients_used, reduced), recs = sorted_ingredients[0]
    for ingredient in reduced:
        rows[row_index].add_ingredient(side, ingredient)
    rows[row_index].add_recipes(side, recs)

    for recipe in recs:
        pending_assignment.remove(recipe)


def build_rows() -> dict:
    rows = initial_lanes()
    pending_assignment = set(products)

    while pending_assignment:
        sorted_ingredients = sort_ingredients(pending_assignment, rows)
        if sorted_ingredients:
            add_ingredients(sorted_ingredients, pending_assignment, rows)
        else:
            rows.append(MallRow())

    # Rebalance rows if possible

    return rows


if __name__ == "__main__":
    rows = build_rows()

    for row in rows:
        print(row)
        print("===============================")

    # for line in sorted(recipes.keys()):
    #     print(line)
