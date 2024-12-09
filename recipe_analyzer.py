from recipes import recipes, get_recipe_ingredients

copper_recipes = sorted(recipe for recipe in recipes.keys() if 'copper-plate' in get_recipe_ingredients(recipe))
print('\n'.join(copper_recipes))
