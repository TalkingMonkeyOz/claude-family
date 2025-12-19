def hello_world(name: str) -> str:
    """
    Returns a greeting string with the given name.
    
    Args:
        name: The name to greet
        
    Returns:
        A greeting string
    """
    return f"Hello, {name}!"


if __name__ == "__main__":
    # Test the function
    result = hello_world("World")
    print(result)
