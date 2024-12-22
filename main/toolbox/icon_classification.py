# box only has x and y
# slice to get what's in the bounding box
#whole image/current frame is array which contains x, y, and three channels for r b g
#index slice via numpy to only look at the part enclosed by the bounding box

# x, y, width, height for each sublist in the list "boxes"


# return list of classifications corresponding to the list of box coordinates

# frame is list r g b for each screenframe, every 3 items in frame is a screenframe. frame is ur entire 3D array.
def icon_classification(frame, boxes):
    print("the frame shape: ")
    print(frame.shape)
    print("the frame: ")
    print(frame)
    print("the size of boxes: ")
    print(len(boxes))
    print("the boxes: ")
    print(boxes)
    #for i in boxes:
    #    print(i)
    print('\n')

    print(len(frame[0]))
    print('\n')

#everytime we loop in main, we store the frame in runtime.color_image
#within aim, since runtime is already imported
# the function is in aim so you can either pass the frame as an
# argument in the function we're defning or you could import runtime
# inside the definition script
# output -> list of classifications for each box

# I'm guessing enemy_boxes is the list of all boxes. Currently it cannot distinguish between enemy and team 
# bots so enemy_boxes is just all detected boxes.