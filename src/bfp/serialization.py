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
