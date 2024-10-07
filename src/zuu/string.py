from string import Formatter as _Formatter
import os
import io
import base64

def is_fstring(string: str):
    """
    Check if a given string is a formatted string literal (f-string).

    Args:
        string (str): The string to be checked.

    Returns:
        bool: True if the string is a formatted string literal, False otherwise.
    """
    if not isinstance(string, str):
        return False
    try:
        _Formatter().parse(string)
        return True
    except ValueError:
        return False


def extract_fstring_keys(string: str):
    """
    Extracts the keys used in a formatted string literal (f-string).

    Args:
        string (str): The formatted string literal.

    Returns:
        list: A list of keys used in the f-string.

    This function takes a formatted string literal (f-string) as input and extracts the keys used in it. It checks if the input is a string and if not, it returns an empty list. If the input is a string, it uses the `Formatter().parse()` method to parse the string and extract the keys. It then returns a list of keys used in the f-string. If any error occurs during the parsing, it returns an empty list.

    Example:
        >>> extract_fstring_keys("Hello, {name}!")
        ['name']
        >>> extract_fstring_keys("The answer is {answer}.")
        ['answer']
        >>> extract_fstring_keys("This is not an f-string.")
        []
    """
    if not isinstance(string, str):
        return []
    try:
        return [x[1] for x in _Formatter().parse(string) if x[1] is not None]
    except ValueError:
        return []


def rreplace(s: str, old: str, new: str, occurrence):
    """
    Replaces the last occurrence of a substring in a string with a new substring.

    Args:
        s (str): The input string.
        old (str): The substring to be replaced.
        new (str): The new substring to replace the old substring.
        occurrence (int): The number of occurrences of the old substring to replace.

    Returns:
        str: The modified string with the last occurrence of the old substring replaced by the new substring.

    Raises:
        None

    Example:
        >>> rreplace("Hello, world!", "world", "codeium", 1)
        'Hello, codeium!'
    """
    if occurrence <= 0:
        return s

    parts = s.rsplit(old, occurrence)
    return new.join(parts)

# ANCHOR markdown

def extract_md_meta(md_content : str):
    """
    Extracts the metadata from the content of a Markdown file.
    
    Args:
        md_content (str): The content of the Markdown file.
    
    Returns:
        dict: The metadata dictionary extracted from the Markdown file.
    """
        
    if "---" not in md_content:
        return {}
    
    meta_start = md_content.index("---") + 3
    meta_end = md_content.index("---", meta_start)
    meta_str = md_content[meta_start:meta_end]

    import yaml
    meta_dict : dict = yaml.safe_load(meta_str)

    return meta_dict


def get_md_meta(md_file : str):
    """
    Retrieves the metadata from a Markdown file.
    
    Args:
        md_file (str): The path to the Markdown file.
    
    Returns:
        dict: The metadata dictionary extracted from the Markdown file.
    """
        
    with open(md_file, "r") as f:
        md_content = f.read()
        return extract_md_meta(md_content)
    
def append_meta(md_content : str, meta_dict : dict):
    """
    Appends the provided metadata dictionary to the Markdown content, either by adding a new metadata block or updating the existing one.
    
    Args:
        md_content (str): The Markdown content to append the metadata to.
        meta_dict (dict): The metadata dictionary to be appended.
    
    Returns:
        str: The updated Markdown content with the appended metadata.
    """
    import yaml
    if "---\n" not in md_content:
        return "---\n" + yaml.safe_dump(meta_dict) + "---\n" + md_content
    

    meta_start = md_content.index("---\n") + 4
    meta_end = md_content.index("---\n", meta_start)
    existing_meta_str = md_content[meta_start:meta_end]
    existing_meta_dict = yaml.safe_load(existing_meta_str)
    
    existing_meta_dict.update(meta_dict)
    updated_meta_str = yaml.safe_dump(existing_meta_dict, sort_keys=False)
    
    return md_content[:meta_start] + updated_meta_str + md_content[meta_end:]



def update_meta(md_file : str, meta_dict : dict):
    """
    Updates the metadata in a Markdown file by merging the existing metadata with the provided metadata dictionary.
    
    Args:
        md_file (str): The path to the Markdown file.
        meta_dict (dict): The metadata dictionary to be merged with the existing metadata.
    
    Returns:
        str: The updated Markdown content with the merged metadata.
   """
      
    if not os.path.exists(md_file):
        existingMeta = {}
    else:
        existingMeta = get_md_meta(md_file)
    existingMeta.update(meta_dict)


    with open(md_file, "r") as f:
        md_content = f.read()
    
    return append_meta(md_content, existingMeta)

def dump_meta(md_file : str, meta_dict : dict):
    """
    Dumps the provided metadata dictionary to a Markdown file.

    Args:
        md_file (str): The path to the Markdown file.
        meta_dict (dict): The metadata dictionary to be dumped.

    Returns:
        None
    """
    with open(md_file, "w") as f:



        f.write(update_meta(md_file, meta_dict))

# base 64


def load_base64_img(string: str):
    """
    Load an image from a base64 encoded string.

    Args:
        string (str): The base64 encoded string representing the image.

    Returns:
        Image: The loaded image object.

    This function takes a base64 encoded string as input and loads an image from it. It checks if the string starts with
    "data:image/png;base64," and removes that prefix if it exists. Then, it decodes the base64 string using the
    `base64.b64decode` function and creates an in-memory bytes object using `io.BytesIO`. Finally, it uses the
    `Image.open` function from the Pillow library to open the image from the bytes object and returns the loaded image.
    """

    from PIL import Image
    if string.startswith("data:image/png;base64,"):
        string = string[22:]
    return Image.open(io.BytesIO(base64.b64decode(string)))


def image_to_base64(img):
    """
    Convert an image to a base64 encoded string.

    Args:
        img (Image): The image to be converted to a base64 encoded string.

    Returns:
        str: The base64 encoded string representation of the image.
    """
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def image_to_base64_markdown(img):
    """
    Convert an image to a base64 encoded string with a data URI prefix.

    Args:
        img (Image): The image to be converted to a base64 encoded string.

    Returns:
        str: The base64 encoded string representation of the image with a data URI prefix.
    """
    return "data:image/png;base64," + image_to_base64(img)


def is_base64(string: str):
    try:
        if string.startswith("data:image/png;base64,"):
            string = string[22:]
        base64.b64decode(string, validate=True)
        return True
    except:  # noqa
        return False
