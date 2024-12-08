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
from typing import Iterable


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
    class Side(Enum):
        TOP = "top"
        BOT = "bottom"

    ingredient_lanes: list[str] = field(default_factory=populated_list)
    recipes_top: list[str] = field(default_factory=list)
    recipes_bot: list[str] = field(default_factory=list)

    def get_side_range(self, side: Side | None) -> slice:
        if side == self.Side.TOP:
            return slice(0, 6)
        elif side == self.Side.BOT:
            return slice(2, 8)
        return slice(0, 8)

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

    def get_ingredients(self, side: Side | None) -> tuple[str]:
        return tuple(self.ingredient_lanes[self.get_side_range(side)])

    def lane_indices(self, side: Side | None) -> Iterable[int]:
        if side == self.Side.TOP:
            return [2, 3, 4, 5, 0, 1]
        if side == self.Side.BOT:
            return [2, 3, 4, 5, 6, 7]
        return [2, 3, 4, 5, 0, 1, 6, 7]

    def full(self, side: Side) -> bool:
        return None not in self.get_ingredients(side)

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
            lines.append(self.ingredient_lanes[i] or "")
        for recipe in sorted(self.recipes_top):
            lines.append(f"    {recipe}")
        for i in [2, 3, 4, 5]:
            lines.append(self.ingredient_lanes[i] or "")
        for recipe in sorted(self.recipes_bot):
            lines.append(f"    {recipe}")
        for i in [6, 7]:
            lines.append(self.ingredient_lanes[i] or "")
        return "\n".join(lines)


def build_rows() -> dict:
    rows = [MallRow(), MallRow()]
    rows[0].ingredient_lanes[0] = "iron-plate"
    # rows[0].ingredient_lanes[1] = "iron-plate"
    rows[0].ingredient_lanes[2] = "iron-gear-wheel"
    rows[0].ingredient_lanes[3] = "electronic-circuit"
    rows[1].ingredient_lanes[0] = "stone"
    rows[1].ingredient_lanes[1] = "stone-brick"
    pending_assignment = set(products)

    while pending_assignment:
        best_by_row = []
        for row_index, row in enumerate(rows):
            for side, row_ingredients in row:
                if row.full(side):
                    continue

                reduced_ingredients = defaultdict(list)
                for recipe in pending_assignment:
                    reduced = tuple(sorted(set(get_ingredients_key(recipe)) - set(row_ingredients)))
                    existing_ingredients_used = len(recipes[recipe]) - len(reduced)
                    reduced_ingredients[(existing_ingredients_used, reduced)].append(recipe)
                sorted_ingredients = sorted(
                    reduced_ingredients.keys(), key=lambda e: (len(e[1]), -e[0], -len(reduced_ingredients[e]))
                )
                best_by_row.append((row_index, side, sorted_ingredients[0], reduced_ingredients[sorted_ingredients[0]]))

        sorted_ingredients = sorted(best_by_row, key=lambda e: (len(e[2][1]), -e[2][0], -len(e[3])))

        found_space = False
        for row_index, side, (existing_ingredients_used, reduced), recs in sorted_ingredients:
            if (
                len(reduced) <= rows[row_index].count_available_lanes(side)
                # and len(rows[row_index].get_recipes(side)) < 8
            ):
                found_space = True
                for ingredient in reduced:
                    rows[row_index].add_ingredient(side, ingredient)
                rows[row_index].add_recipes(side, recs)

                for recipe in recs:
                    pending_assignment.remove(recipe)
                break

        if not found_space:
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
