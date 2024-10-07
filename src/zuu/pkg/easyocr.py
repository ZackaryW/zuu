import typing
import io
import numpy
import easyocr


def get_coords(
    image: typing.Union[str, bytes, numpy.ndarray, io.BytesIO],
    lang: typing.List[str] = ["en"],
    mode: str = "text",
    additionalReaderArgs: typing.Dict = {},
):
    """
    Extracts the coordinates of text or paragraphs in an image using the EasyOCR library.

    Args:
        image (typing.Union[str, bytes, numpy.ndarray, io.BytesIO]): The input image. It can be a file path, bytes,
            numpy array, or an io.BytesIO object.
        lang (typing.List[str], optional): The list of languages to recognize. Defaults to ["en"].
        mode (str, optional): The mode of extraction. Can be "text" for text coordinates or "paragraph" for paragraph
            coordinates. Defaults to "text".
        additionalReaderArgs (typing.Dict, optional): Additional arguments to pass to the EasyOCR reader.
            Defaults to {}.

    Returns:
        List[Tuple[Tuple[int, int], Tuple[int, int], float, str]]: A list of tuples containing the coordinates of the
            detected text or paragraphs in the image. Each tuple contains the bottom left and top right coordinates,
            the confidence level, and the recognized text.

    Raises:
        ValueError: If an invalid mode is provided.

    Example:
        >>> image_path = "path/to/image.jpg"
        >>> text_coords = get_coords(image_path, mode="text")
        >>> paragraph_coords = get_coords(image_path, mode="paragraph")
        >>> print(text_coords)
        >>> print(paragraph_coords)
    """
    if mode not in ["text", "paragraph"]:
        raise ValueError("Invalid mode. Use 'text' or 'paragraph'.")

    if mode == "paragraph":
        additionalReaderArgs["paragraph"] = True

    reader = easyocr.Reader(lang_list=lang)

    if isinstance(image, io.BytesIO):
        image = numpy.array(image)

    result = reader.readtext(image, **additionalReaderArgs)
    coordinates = []
    for detection in result:
        bottom_left = detection[0][0]
        top_right = detection[0][2]
        confidence = detection[1]
        text = detection[2]
        coordinates.append((bottom_left, top_right, confidence, text))

    return coordinates
