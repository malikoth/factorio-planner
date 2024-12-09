# CAUTION: The following command disables achievements. Do not use on primary savefiles
# Dump raw recipe data in-game with the following console command:
# /c local list = {} for _, recipe in pairs(game.player.force.recipes) do list[#list+1] = {recipe.name,{recipe.ingredients}} end helpers.write_file("recipes.txt", serpent.block(list))

from collections import defaultdict

from mallrow import MallRow
from recipes import exclusive_products, get_recipe_ingredients, products, recipes


def find_best_ingredients(
    row: MallRow, side: MallRow.Side, pending_assignment: set[str]
) -> tuple[tuple[str], list[str]]:
    """Find the best ingredient(s) to add to one side of a MallRow

    Also include the list of recipes enabled by the best ingredient(s) in the return
    """

    reduced_ingredients = defaultdict(list)

    for recipe in pending_assignment:
        reduced = tuple(sorted(set(get_recipe_ingredients(recipe)) - set(row.get_ingredients(side))))
        existing_ingredients_used = len(recipes[recipe]) - len(reduced)

        if (
            row.get_ingredients(side).count(None) >= len(reduced)
            and not row.full(side)
            and (recipe not in exclusive_products or len(set(row.get_recipes(side)) & exclusive_products) == 0)
        ):
            reduced_ingredients[(existing_ingredients_used, reduced)].append(recipe)

    # Sort candidate ingredients by:
    #   1. require the fewest new ingredients
    #   2. use the most existing ingredients
    #   3. enable the most number of new recipes
    sorted_ingredients = sorted(
        reduced_ingredients.keys(), key=lambda e: (len(e[1]), -e[0], -len(reduced_ingredients[e]))
    )

    if sorted_ingredients:
        return sorted_ingredients[0], reduced_ingredients[sorted_ingredients[0]]
    return (), []


def sort_ingredients(
    pending_assignment: set[str], rows: list[MallRow]
) -> list[tuple[int, MallRow.Side, tuple[str], list[str]]]:
    """Find candidates for an ingredient to add to a lane on each side of each row"""
    best_by_row = []
    for row_index, row in enumerate(rows):
        for side in row:
            ingredients, new_recipes = find_best_ingredients(row, side, pending_assignment)
            if not new_recipes:
                continue

            best_by_row.append((row_index, side, ingredients, new_recipes))
    return sorted(best_by_row, key=lambda e: (len(e[2][1]), -e[2][0], -len(e[3])))


def build_rows() -> dict:
    rows = []
    pending_assignment = set(products)
    for row in rows:
        pending_assignment -= set(row.recipes_top + row.recipes_bot)

    while pending_assignment:
        sorted_ingredients = sort_ingredients(pending_assignment, rows)
        if sorted_ingredients:
            row_index, side, (_, reduced), new_recipes = sorted_ingredients[0]
            for ingredient in reduced:
                rows[row_index].add_ingredient(side, ingredient)

            for recipe in new_recipes:
                if rows[row_index].full(side):
                    break

                rows[row_index].add_recipe(side, recipe)
                pending_assignment.remove(recipe)
        else:
            rows.append(MallRow())

    return rows


if __name__ == "__main__":
    rows = build_rows()

    for row in rows:
        print(row)
        print("===============================")
