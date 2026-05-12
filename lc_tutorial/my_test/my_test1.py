
import os
import sys
from dotenv import load_dotenv
load_dotenv(override=True)
# Ensure tools.py can be imported regardless of working directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools import weather_condition, city_population, country_capital, fruit_color, animal_sound
from deepagents import create_deep_agent

test_agent = create_deep_agent(
    model="openai:gpt-4o-mini",
    tools=[weather_condition, city_population, country_capital, fruit_color, animal_sound], 

)

result = test_agent.invoke({"messages": [{"role": "user", "content": "for uk, france and germany, determine capitals and populations"}]})

print(result["messages"][-1].content)