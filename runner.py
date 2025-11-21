import os

import django


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from helpers.utils import read_json_generator

def check_empty_cities():
	location_data = read_json_generator("apps/core/location_seeder/countries+states+cities.json")
	data = []
	for dt in location_data:
		sub_data = dict(country=dt["name"], no_of_states=0, states=[])
		states = dt["states"]
		for state_data in states:
			state = state_data["name"]
			cities = state_data["cities"]
			if not cities:
				sub_data["no_of_states"] += 1
				sub_data["states"].append(state)
		if sub_data["no_of_states"] > 0:
			data.append(sub_data)
	return data

data = check_empty_cities()
print(len(data))
