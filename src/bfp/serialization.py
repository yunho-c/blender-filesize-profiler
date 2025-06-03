import yaml

def serialize_to_yaml(data, output_path):
    """
    Serializes the given data to a YAML file.

    :param data: The data to serialize (should be a dictionary or list).
    :param output_path: The path to the output YAML file.
    """
    try:
        with open(output_path, 'w') as f:
            yaml.dump(data, f, indent=2, sort_keys=False)
        print(f"Successfully serialized analysis to {output_path}")
    except Exception as e:
        print(f"Error serializing to YAML: {e}")

def load_from_yaml(file_path):
    """
    Loads data from a YAML file.

    :param file_path: The path to the input YAML file.
    :return: The loaded data (typically a dictionary or list), or None if an error occurs.
    """
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        print(f"Successfully loaded data from {file_path}")
        return data
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file {file_path}: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading {file_path}: {e}")
        return None
