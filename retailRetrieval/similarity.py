import cv2
import os
import pickle
import numpy as np

class Extractor:
    def __init__(self, algo = None):
        self.bf = cv2.BFMatcher()
        self.algo = algo

    def imageResize(self, image):
        maxD = 1024
        height,width = image.shape
        aspectRatio = width/height
        if aspectRatio < 1:
            newSize = (int(maxD*aspectRatio),maxD)
        else:
            newSize = (maxD,int(maxD/aspectRatio))
        image = cv2.resize(image,newSize)
        return image

    def classReader(self, path):
        class_paths = os.listdir(path)
        img = []
        name = []
        for cls in class_paths:
            img_paths = os.listdir(path + '/' + cls)
            for img_name in img_paths:
                img_path = path + '/' + str(cls) + '/' + str(img_name)
                img.append(self.imageResize(cv2.imread(img_path,0)))
                name.append(img_name)
        return img, name

    def computeDescriptors(self, image):
        if self.algo == 'SIFT':
            return cv2.SIFT_create().detectAndCompute(image, None)
        if self.algo == 'ORB':
            return cv2.ORB_create().detectAndCompute(image, None)
        if self.algo == None:
            assert AssertionError
        
    def saveAnchor(self, keypoints, descriptors, img_name, path):
        if self.algo == 'SIFT':
            path = os.path.join(path, 'sift')
        else:
            path = os.path.join(path, 'orb')
        
        os.makedirs(os.path.join(path, 'keypoints'))
        os.makedirs(os.path.join(path, 'descriptors'))

        for i,keypoint in enumerate(keypoints):
            deserializedKeypoints = []
            filepath = os.path.join(path, 'keypoints', str(img_name[i].split('.')[0]) + ".txt")
            for point in keypoint:
                temp = (point.pt, point.size, point.angle, point.response, point.octave, point.class_id)
                deserializedKeypoints.append(temp)
            with open(filepath, 'wb') as fp:
                pickle.dump(deserializedKeypoints, fp)
        
        for i,descriptor in enumerate(descriptors):
            filepath = os.path.join(path, 'descriptors', str(img_name[i].split('.')[0]) + ".txt")
            with open(filepath, 'wb') as fp:
                pickle.dump(descriptor, fp)
    
    def fetchKeypointFromFile(self, filepath):
        keypoint = []
        file = open(filepath,'rb')
        deserializedKeypoints = pickle.load(file)
        file.close()
        for point in deserializedKeypoints:
            temp = cv2.KeyPoint(
                x=point[0][0],
                y=point[0][1],
                size=point[1],
                angle=point[2],
                response=point[3],
                octave=point[4],
                class_id=point[5]
            )
            keypoint.append(temp)
        return keypoint
    
    def fetchDescriptorFromFile(self, filepath):
        file = open(filepath,'rb')
        descriptor = pickle.load(file)
        file.close()
        return descriptor
    
    def calculateScore(self, matches,keypoint1,keypoint2):
        return 100 * (matches/min(keypoint1,keypoint2))
    
    def calculateMatches(self,des1,des2):
        matches = self.bf.knnMatch(des1,des2,k=2)
        topResults1 = []
        for m,n in matches:
            if m.distance < 0.7*n.distance:
                topResults1.append([m])
                
        matches = self.bf.knnMatch(des2,des1,k=2)
        topResults2 = []
        for m,n in matches:
            if m.distance < 0.7*n.distance:
                topResults2.append([m])
        
        topResults = []
        for match1 in topResults1:
            match1QueryIndex = match1[0].queryIdx
            match1TrainIndex = match1[0].trainIdx

            for match2 in topResults2:
                match2QueryIndex = match2[0].queryIdx
                match2TrainIndex = match2[0].trainIdx

                if (match1QueryIndex == match2TrainIndex) and (match1TrainIndex == match2QueryIndex):
                    topResults.append(match1)
        return topResults
    
    def calculateResultsFor(self, keypoint1, keypoint2, descriptor1, descriptor2):
        matches = self.calculateMatches(descriptor1, descriptor2)
        score = self.calculateScore(len(matches),len(keypoint1),len(keypoint2))
        return score
    
    def classRepresent(self, path):
        img, name = self.classReader(path)

        keypoints = []
        descriptors = []
        for image in img:
            keypointTemp, descriptorTemp = self.computeDescriptors(image)
            keypoints.append(keypointTemp)
            descriptors.append(descriptorTemp)
        
        self.saveAnchor(keypoints = keypoints, descriptors = descriptors, img_name = name, path = 'class_database')

    def classInfo(self, class_path):
        class_paths = os.listdir(class_path)
        name = []
        label = []
        for cls in class_paths:
            img_paths = os.listdir(class_path + '/' + cls)
            for img_name in img_paths:
                #img_path = class_path + '/' + str(cls) + '/' + str(img_name)
                name.append(img_name)
                label.append(cls)
        return name, label
    
    def retriveClasses(self, database_path, class_path):
        img_names, labels = self.classInfo(class_path)
        if self.algo == 'SIFT':
            stored_keypoint = os.path.join(database_path, 'sift/keypoints')
            stored_descriptor = os.path.join(database_path, 'sift/descriptors')
        if self.algo == 'ORB':
            stored_keypoint = os.path.join(database_path, 'orb/keypoints')
            stored_descriptor = os.path.join(database_path, 'orb/descriptors')
        
        keypoints = []
        descriptors = []
        for img_name in img_names:
            keypoints.append(self.fetchKeypointFromFile(stored_keypoint + '/' + str(img_name.split('.')[0]) + '.txt'))
            descriptors.append(self.fetchDescriptorFromFile(stored_descriptor + '/' + str(img_name.split('.')[0]) + '.txt'))
        return keypoints, descriptors, labels

    def processClass(self, crop_img, database_keypoints, database_descriptors, class_labels):
        image = cv2.cvtColor(crop_img, cv2.COLOR_RGB2GRAY)
        image = self.imageResize(image)
        keypoint1, descriptor1 = self.computeDescriptors(image)
        res = []

        for (keypoint2, descriptor2) in zip(database_keypoints, database_descriptors):
            res.append(self.calculateResultsFor(keypoint1, keypoint2, descriptor1, descriptor2))
        return class_labels[np.argmax(res)]