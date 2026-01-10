import sys
import yaml
import numpy as np
from pykml import parser

class NumpyArrayEncoder(yaml.YAMLObject):
    yaml_tag = ''

    def __init__(self, data):
        self.data = data

    @classmethod
    def to_yaml(cls, dumper, data):
        np_array_str = np.array2string(data.data, separator=' ')
        return dumper.represent_scalar(cls.yaml_tag, np_array_str, style='|')


def main():
    airport = input("Enter airport name: ")
    ref_lat = float(input("Enter reference latitude: "))
    ref_lon = float(input("Enter reference longitude: "))
    max_alt = int(input("Enter maximum altitude: "))
    
    fence = parse_coordinates(coordinates_str)
    
    data = {
        'airport': airport,
        'ref_lat': ref_lat,
        'ref_lon': ref_lon,
        'max_alt': max_alt,
    }
    
    with open("./conf/airports/"+ airport + "_output.yaml", 'w') as file:
        yaml.dump(data, file, default_flow_style=False, sort_keys=False)
    
    print(f"YAML file created: {airport}_output.yaml")

if __name__ == "__main__":
    main()