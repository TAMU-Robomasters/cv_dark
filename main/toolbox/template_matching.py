import cv2 as cv
import numpy as np
from matplotlib import pyplot as plt
 
img_rgb = cv.imread('template_matching_photos/test1.jpg')
img_gray = cv.cvtColor(img_rgb, cv.COLOR_BGR2GRAY)
assert img_rgb is not None, "file could not be read, check with os.path.exists()"
img2 = img_gray.copy()
template = cv.imread('template_matching_photos/test1_template.jpg', cv.IMREAD_GRAYSCALE)
assert template is not None, "file could not be read, check with os.path.exists()"
w, h = template.shape[::-1]
 
# All the 6 methods for comparison in a list
methods = ['cv.TM_CCOEFF', 'cv.TM_CCOEFF_NORMED', 'cv.TM_CCORR',
 'cv.TM_CCORR_NORMED', 'cv.TM_SQDIFF', 'cv.TM_SQDIFF_NORMED']

res = cv.matchTemplate(img2,template,cv.TM_CCOEFF_NORMED)
threshold = 0.8
loc = np.where( res >= threshold)
for pt in zip(*loc[::-1])
    cv.rectangle(img_rgb, pt, (pt[0] + w, pt[1] + h), (255,0,255), 2)
 
# for meth in methods:
#  img = img2.copy()
#  method = eval(meth)
 
#  # Apply template Matching
#  res = cv.matchTemplate(img,template,method)
#  min_val, max_val, min_loc, max_loc = cv.minMaxLoc(res)
 
#  # If the method is TM_SQDIFF or TM_SQDIFF_NORMED, take minimum
#  if method in [cv.TM_SQDIFF, cv.TM_SQDIFF_NORMED]:
#     top_left = min_loc
#  else:
#     top_left = max_loc
#     bottom_right = (top_left[0] + w, top_left[1] + h)
 
#  cv.rectangle(img,top_left, bottom_right, 255, 2)
 
plt.subplot(131),plt.imshow(img2, cmap='gray')
plt.title('Image Input'), plt.xticks([]), plt.yticks([])
plt.subplot(132),plt.imshow(template, cmap='gray')
plt.title('Template Input'), plt.xticks([]), plt.yticks([])
plt.subplot(133),plt.imshow(img_rgb)
plt.title('Result'), plt.xticks([]), plt.yticks([])
#  plt.suptitle(meth)

plt.show()