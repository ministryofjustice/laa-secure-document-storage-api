def validate_file_type(file_path, allowed_types):
    """
    Validates the file type of the given file against the allowed types.

    Args:
    - file_path (str): Path to the file to be validated.
    - allowed_types (list of str): List of allowed file types.

    Returns:
    - bool: True if the file type is allowed, False otherwise.
    """


# Example usage
file_path = "example.txt"
allowed_types = ["text/plain", "application/pdf"]

if validate_file_type(file_path, allowed_types):
    print("File type is allowed.")
else:
    print("File type is not allowed.")
