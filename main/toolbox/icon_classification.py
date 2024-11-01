
import cv2
from toolbox.drew_tools.drew_image_tools import find_and_draw_contours

def detect_numbers(frame, bounding_boxes, DEBUG:bool=False):
    find_and_draw_contours(frame, frame.copy(), save_output=DEBUG)
    # bounding_boxes is a list of box coordinates --> x, y, width, height
    # valid_boxes from aim.py is the list of bounding boxes to run icon detection on
    # frame is 3d array --> x, y, [r, g, b], (rows, columns, channels)
    print(frame[0][0]) # x, y




def get_cropped_image(frame, bounding_boxes, show_image:bool=True):
    """ Gets cropped image of armor panel from frame. """
    # list of cropped images
    cropped_images = []
    n = 0 # Current box

    # we need to extract x, y, width, height from bounding box
    for box in bounding_boxes:
        x = int(box.x_top_left)
        y = int(box.y_top_left)
        width = int(box.width)
        height = int(box.height)

        
        # slice cropped image from frame
        cropped_image = frame[y:y+height+1, x:x+width+1, :]

        # insert into list
        cropped_images.append(cropped_image)

        cv2.imwrite(f"toolbox/cropped/cropped_image_{n}.jpg", cropped_image) #DEBUG
        n += 1

        # show cropped image
        if show_image:
            cv2.imshow("Cropped image", cropped_image)
            cv2.waitKey()

        # testing to see shape of cropped image
        #print(cropped_image.shape)
    
    if show_image:
        cv2.destroyAllWindows()
    
    #raise Exception("This will stop the program for debug purposes.")

    return cropped_images


def predict_icons(frame, bounding_boxes, DEBUG:bool=False):

    if DEBUG: print(f"[icon_classification.py][predict_icon] Cropping {len(bounding_boxes)} images")
    cropped_imgs = get_cropped_image(frame, bounding_boxes, show_image=False)
    if DEBUG: print("[icon_classification.py][predict_icon] Images cropped. Detecting numbers")
    numbers = []
    for cropped_icon in cropped_imgs:
        numbers.append(detect_numbers(cropped_icon, bounding_boxes, DEBUG=DEBUG))
    
    # Stop the program if DEBUG is true before returning
    if DEBUG:
        if DEBUG: print(f"[icon_classification.py][predict_icon] Numbers detected ({numbers})")
        raise Exception("DEBUG is True - Stopping program.")

    return "placeholder icon name"
