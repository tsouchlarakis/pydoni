import pydoni


def make_meme(
        image_file,
        output_file,
        msg,
        msg_color='white',
        msg_pos='bottom',
        msg_outline_color='black',
        msg_outline_width=3,
        # font_path='/System/Library/Fonts/HelveticaNeue.ttc',
        font_path='/Library/Fonts/Arial Black.ttf',
        font_size=200,
        repel_from_edge=0.0):
    """
    Draw text on an image file.

    :param image_file: image file to draw on
    :type image_file: str
    :param output_file: filepath to save output image to
    :type output_file: str
    :param msg: message to write on image
    :type msg: str
    :param msg_color: color of message
    :type msg_color: str
    :param msg_pos: position of message, only 'bottom' supported
    :type msg_pos: str
    :param msg_outline_color: message outline color
    :type msg_outline_color: str
    :param msg_outline_width: width of text outline
    :type msg_outline_width: int
    :param font_path: path to font to use
    :type font_path: str
    :param font_size: desired font size of `msg`
    :type font_size: int
    :param repel_from_edge: shift text position this % of the image
        height/width away from the edge if text position is an edge of
        the image. Example: if the specified position is top-left, the text
        will be printed right up against the top and left edges. If a value
        of 0.05 is specified for `repel_from_edge`, then the text will be
        shifted down 5% of the image height and shifted right 5% of the
        image width
    :type repel_from_edge: float
    """

    from PIL import Image
    from PIL import ImageFont
    from PIL import ImageDraw

    img = Image.open(image_file)
    draw = ImageDraw.Draw(img)

    lines = []

    font = ImageFont.truetype(font_path, font_size)
    w, h = draw.textsize(msg, font)

    imgWidthWithPadding = img.width * 0.99

    # 1. How many lines for the msg to fit ?
    lineCount = 1
    if w > imgWidthWithPadding:
        lineCount = int(round((w / imgWidthWithPadding) + 1))

    if lineCount > 2:
        while 1:
            font_size -= 2
            font = ImageFont.truetype(font_path, font_size)
            w, h = draw.textsize(msg, font)
            lineCount = int(round((w / imgWidthWithPadding) + 1))
            if lineCount < 3 or font_size < 10:
                break

    # If msg contains no spaces but is long enough to justify multiple
    # lines, revert to lineCount = 1 as the next part will fail, attempting
    # to split the message into multiple lines on a space
    if lineCount > 1 and ' ' not in msg:
        lineCount = 1

    # 2. Divide text in X lines
    lastCut = 0
    isLast = False
    for i in range(0,lineCount):
        if lastCut == 0:
            cut = (len(msg) / lineCount) * i
        else:
            cut = lastCut

        if i < lineCount-1:
            nextCut = (len(msg) / lineCount) * (i+1)
        else:
            nextCut = len(msg)
            isLast = True

        # Make sure we don't cut words in half
        nextCut = int(nextCut)
        nextCutOriginal = nextCut
        if nextCut == len(msg) or msg[nextCut] == " ":
            pass
        else:
            # Check forward and backward from nextCut to get position of
            # string to cut at (look for nearest whitespace)
            while msg[nextCut] != " ":
                if nextCut == len(msg)-1:
                    nextCut = nextCutOriginal
                    break
                nextCut += 1

            while msg[nextCut] != " ":
                nextCut -= 1

        cut = int(cut)
        line = msg[cut:nextCut].strip()

        # Is line still fitting?
        w, h = draw.textsize(line, font)
        if not isLast and w > imgWidthWithPadding:
            nextCut -= 1
            while msg[nextCut] != " ":
                nextCut -= 1

        lastCut = nextCut
        lines.append(msg[cut:nextCut].strip())

    lastY = -h
    if msg_pos == "bottom":
        repel_pixels = repel_from_edge * img.height
        repel_pixels = int(repel_pixels)
        lastY = img.height - h * (lineCount+1) - repel_pixels

    for i in range(0,lineCount):
        w, h = draw.textsize(lines[i], font)
        textX = img.width/2 - w/2
        textY = lastY + h

        mow = msg_outline_width
        moc = msg_outline_color
        if moc is not None:
            draw.text((textX-mow, textY-mow), lines[i], moc, font=font)
            draw.text((textX+mow, textY-mow), lines[i], moc, font=font)
            draw.text((textX+mow, textY+mow), lines[i], moc, font=font)
            draw.text((textX-mow, textY+mow), lines[i], moc, font=font)

        draw.text((textX, textY), lines[i], msg_color, font=font)
        lastY = textY

    img.save(output_file)


def ocr_image(imagefile, preprocess=None):
    """
    Apply PyTesseract OCR to an image file.
    Source: https://www.pyimagesearch.com/2017/07/10/using-tesseract-ocr-python/

    :param imagefile: path to image file
    :type imagefile: int
    :param preprocess: any preprocessing steps to apply
    :type preprocess: str
    :return: OCR text string
    :rtype: str
    """
    import cv2
    import pytesseract
    import os
    from PIL import Image

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    # Load the example image and convert it to grayscale
    image = cv2.imread(imagefile)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    logger.info('Image converted to grayscale')

    # Check to see if we should apply thresholding to preprocess the image
    if isinstance(preprocess, str):
        if preprocess == 'thresh':
            gray = cv2.threshold(gray, 0, 255,
                cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
            logger.info('Thresholding applied in image preprocessing')

        # Make a check to see if median blurring should be done to remove noise
        elif preprocess == 'blur':
            gray = cv2.medianBlur(gray, 3)
            logger.info('Anti-blurring applied in image preprocessing')

        else:
            logger.warn("Unknown `preprocess` parameter '%s', continuing without preprocessing" % preprocess)

    else:
        logger.info('No image preprocessing applied')

    # Write the grayscale image to disk as a temporary file so we can
    # apply OCR to it
    tmpfile = '{}.png'.format(os.getpid())
    cv2.imwrite(tmpfile, gray)
    logger.info("Temporary grayscale file created at '%s'" % tmpfile)

    # Load the image as a PIL/Pillow image, apply OCR, and then delete
    # the temporary file
    logger.info('Applying PyTesseract OCR...')
    text = pytesseract.image_to_string(Image.open(tmpfile))
    logger.info('PyTesseract OCR done!')

    if os.path.isfile(tmpfile):
        os.remove(tmpfile)
        logger.info('Removed temporary greyscale file')

    logger.info('OCR complete')
    return text


def get_blur_value(imagefile):
    """
    Detect the Laplacian blur value of an image file.

    :param file {str} path to image file
    :return {float}: Laplacian blur value
    :source https://pysource.com/2019/09/03/detect-when-an-image-is-blurry-opencv-with-python/
    """

    import cv2

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    img = cv2.imread(imagefile)
    laplacian = cv2.Laplacian(img, cv2.CV_64F)
    laplacian_var = laplacian.var()

    return laplacian_var
