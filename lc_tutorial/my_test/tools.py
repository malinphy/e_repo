

def weather_condition(city:str):
    """Run weather conditions of the given city"""
    city_dict = {"london":"rainy",
     "paris": "sunny", 
     "berlin": "foggy",
     "moscow": "snowy"}
    
    return city_dict[city.lower().strip()]

def city_population(city: str):
    """Run population of the given city"""
    population_dict = {"london": 8900000, "paris": 2140000, "berlin": 3600000, "moscow": 11920000}
    return population_dict[city.lower().strip()]

def country_capital(country: str):
    """Determine the capital of the given country"""
    capital_dict = {"uk": "london", "france": "paris", "germany": "berlin", "russia": "moscow"}
    return capital_dict[country.lower().strip()]

def fruit_color(fruit: str):
    """Determine the color of the given fruit"""
    color_dict = {"apple": "red", "banana": "yellow", "grape": "purple", "lemon": "yellow"}
    return color_dict[fruit.lower().strip()]

def animal_sound(animal: str):
    """Determine the sound of the given animal"""
    sound_dict = {"dog": "bark", "cat": "meow", "cow": "moo", "sheep": "baa"}
    return sound_dict[animal.lower().strip()]


