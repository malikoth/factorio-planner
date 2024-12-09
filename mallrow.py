from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar, Iterable


@dataclass
class MallRow:
    MAX_LANES: ClassVar[int] = 8
    MAX_RECIPES: ClassVar[int] = 10

    class Side(Enum):
        TOP = "top"
        BOT = "bottom"

    ingredient_lanes: list[str] = field(default_factory=list)
    recipes_top: list[str] = field(default_factory=list)
    recipes_bot: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.ingredient_lanes) < self.MAX_LANES:
            self.ingredient_lanes += [None] * (self.MAX_LANES - len(self.ingredient_lanes))

    def full(self, side: Side) -> bool:
        return len(self.get_recipes(side)) >= self.MAX_RECIPES

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

    def add_recipe(self, side: Side, recipe: str) -> None:
        if side == self.Side.TOP:
            self.recipes_top.append(recipe)
        elif side == self.Side.BOT:
            self.recipes_bot.append(recipe)

    def get_ingredients(self, side: Side) -> tuple[str]:
        return tuple(self.ingredient_lanes[self.get_side_range(side)])

    def lane_indices(self, side: Side) -> Iterable[int]:
        if side == self.Side.TOP:
            return [2, 3, 4, 5, 0, 1]
        if side == self.Side.BOT:
            return [2, 3, 4, 5, 6, 7]

    def add_ingredient(self, side: Side, ingredient: str) -> None:
        for lane in self.lane_indices(side):
            if self.ingredient_lanes[lane] is None:
                self.ingredient_lanes[lane] = ingredient
                return
        raise Exception("All ingredient lanes full")

    def __iter__(self):
        yield from self.Side

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
