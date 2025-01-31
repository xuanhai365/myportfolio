from inference import billsOCR
import cv2

billsOCR = billsOCR()
img = cv2.imread('/content/det_dataset/test/images/test_10.jpg')
source = '/content/det_dataset/test/images'
billsOCR.inference(img, output='/content/output')