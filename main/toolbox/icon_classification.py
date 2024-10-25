import cv2
def detect_numbers(frame, bounding_boxes):
    # bounding_boxes is a list of box coordinates --> x, y, width, height
    # valid_boxes from aim.py is the list of bounding boxes to run icon detection on
    # frame is 3d array --> x, y, [r, g, b], (rows, columns, channels)
    print(frame[0][0]) # x, y




def get_cropped_image(frame, bounding_boxes): # from frame gets cropped image of armor panel
    # list of cropped images
    cropped_images = []

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

        # show cropped image
        cv2.imwrite('/Users/amasud7/Desktop/roboMasterCV/cv_dark.git/main/subsystems/log/videos/cropped_image.jpg', cropped_image)
        cv2.imshow("Cropped image", cropped_image)
        cv2.waitKey()

        # testing to see shape of cropped image
        #print(cropped_image.shape)
    

    # return cropped_images

    cv2.destroyAllWindows()