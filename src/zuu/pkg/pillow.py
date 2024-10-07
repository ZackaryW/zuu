from PIL import Image
import numpy as np

def is_mono_color(image: Image.Image):
    """
    A function to check if all pixels in the image have the same color as the first pixel.

    Parameters:
        image: The image to check for mono-color.

    Returns:
        True if all pixels are the same color, False otherwise.
    """
    first_pixel = image.getpixel((0, 0))

    # Check if all pixels are the same as the first pixel
    for x in range(image.width):
        for y in range(image.height):
            if image.getpixel((x, y)) != first_pixel:
                return False
    return True


def count_unique_colors(image: Image) -> int:
    """
    Calculate the number of unique colors in the image.

    Args:
        image (Image): The image to analyze.

    Returns:
        int: The number of unique colors in the image.
    """
    # Convert image to an array and reshape
    image_array = np.array(image)
    reshaped_array = image_array.reshape(-1, image_array.shape[-1])
    # Count unique colors
    unique_colors = len(np.unique(reshaped_array, axis=0))
    return unique_colors
