import importlib.util
import os

SKILLS_DIR = os.path.join(os.path.dirname(__file__), '..', 'my_test')

# List all Python files in the skills directory (excluding __init__.py)
skill_files = [f for f in os.listdir(SKILLS_DIR) if f.endswith('.py') and f != '__init__.py']

# Dynamically import all functions from the skill files
def load_skills():
    skills = {}
    for file in skill_files:
        module_name = file[:-3]
        file_path = os.path.join(SKILLS_DIR, file)
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for attr in dir(module):
            if not attr.startswith('_') and callable(getattr(module, attr)):
                skills[attr] = getattr(module, attr)
    return skills

def main():
    skills = load_skills()
    print('Available skills:', list(skills.keys()))
    # Example usage: call each skill with a sample input
    print('Sample outputs:')
    print('weather_condition("London"):', skills['weather_condition']('London'))
    print('city_population("Paris"):', skills['city_population']('Paris'))
    print('country_capital("Germany"):', skills['country_capital']('Germany'))
    print('fruit_color("Banana"):', skills['fruit_color']('Banana'))
    print('animal_sound("Dog"):', skills['animal_sound']('Dog'))

if __name__ == '__main__':
    main()
