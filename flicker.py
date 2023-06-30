import cv2
import argparse
from skimage.metrics import structural_similarity as ssim
import numpy as np
from hide_face_robust import Box,detect_faces,draw_box,get_video_properties
from mtcnn.mtcnn import MTCNN
from tqdm import tqdm
thres=80
default_shape='rect'
shape_choices=['rect', 'circle', 'oval']
default_distance_threshold = 0.1
default_time_delta = 1
def parse_args():

    file_des='''
    Removes flickers 
    '''
    parser = argparse.ArgumentParser(
        description=file_des, formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('-if', '--inpath_fsgan', type=str, required=True, help='path to fsgan anonymized video')
    parser.add_argument('-io', '--inpath_original', type=str, required=True, help='path to unanonymized video')
    parser.add_argument('-op', '--outpath',type=str,required=True,help='outpath of the final video')
    parser.add_argument('--shape', default=default_shape, choices=shape_choices, help='shape for artifact')
    parser.add_argument('--time_delta', type=int, default=default_time_delta, help='time delta')

    return parser.parse_args()
temp=[]
def mse(imageA, imageB):
	# the 'Mean Squared Error' between the two images is the
	# sum of the squared difference between the two images;
	# NOTE: the two images must have the same dimension

    err = np.sum((imageA.astype("float") - imageB.astype("float")) ** 2)
    err /= float(imageA.shape[0] * imageA.shape[1])
    
	# return the MSE, the lower the error, the more "similar"
	# the two images are
    return err
def compute_similarity(faces_fs,fs_frame,faces_or,or_frame):
    anno_dict={}
    i=0
    for face in faces_fs:
        #crop face
        x, y, w, h = face
        face1=fs_frame[y:y+h, x:x+w]
        face2=or_frame[y:y+h, x:x+w]
        sim=mse(cv2.cvtColor(face1,cv2.COLOR_BGR2GRAY),cv2.cvtColor(face2,cv2.COLOR_BGR2GRAY))
        temp.append(sim)
        if sim>thres:
            anno_dict[i]=0
        else:
            anno_dict[i]=1

        i=i+1
    return anno_dict

if __name__=='__main__':
    try:
        args=parse_args()

        inpath_fsgan=args.inpath_fsgan
        inpath_original=args.inpath_original
        fs_v=cv2.VideoCapture(inpath_fsgan)
        or_v=cv2.VideoCapture(inpath_original)

        fs_v_length=int(fs_v.get(cv2.CAP_PROP_FRAME_COUNT))
        or_v_length=int(or_v.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_count, fps, width, height = get_video_properties(fs_v)

    # video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(args.outpath, fourcc, fps, (width, height))
    
    # white color for hider artifacts
        white_color = (255, 255, 255)
        print(fs_v_length)
        print(or_v_length)
        i=0
        j=0
        fs_list=[]
        or_list=[]
        while(fs_v.isOpened() or or_v.isOpened()):

            if fs_v.isOpened():
                try:
                    _,fs_frame=fs_v.read()
                    if fs_frame.any()==False:
                        break 
                    # cv2.imwrite(f"/home/saksham/Desktop/RED_HEN/fs_frame/frame{i}.png",fs_frame)
                    i=i+1
                    # print(i)
                    fs_list.append(fs_frame)
                    #store images in a list fs_arr
                except:
                    break
            if or_v.isOpened():
                try:
                    _,or_frame=or_v.read()
                    if or_frame.any()==False:
                        break
                    # cv2.imwrite(f"/home/saksham/Desktop/RED_HEN/or_frame/frame{j}.png",or_frame)
                    j=j+1
                    or_list.append(or_frame)
                    #store images in a list or_arr
                except:
                    break

        print("reading frames complete")
        # print(len(fs_list))
        # print(len(or_list))
        # print(i)
        # print(j)
        # remove i-j starting elements from fs_frame
        if i-j>0:
            fs_list=fs_list[i-j:]
        print(len(fs_list))
        mtcnn=MTCNN()
        boxes_nearby_times = dict()
        frames_nearby_times = dict()
        
        for nframe in tqdm(range(len(fs_list))):
            # pass
            faces_fs=detect_faces(fs_list[nframe],mtcnn)
            faces_or=detect_faces(or_list[nframe],mtcnn)
            frames_nearby_times[nframe]=fs_list[nframe]
            boxes_nearby_times[nframe] = [Box(*face) for face in faces_fs]
            if faces_fs:
                do_anno=compute_similarity(faces_fs,fs_list[nframe],faces_or,or_list[nframe])
                print(do_anno)
                # 0 or 1 

            # for anno in do_anno:
            a=0
            for anno in do_anno.values():
                a= (a|anno)
                
            # print(a)
    
            prev_prev_t = nframe - 2 * args.time_delta
            prev_t = nframe - args.time_delta
            this_t = nframe
            next_t = nframe + args.time_delta
            if a or len(faces_fs)==0:
        # see nearby frames
                if prev_t < 0:
                    pass          
                elif prev_t >= 0 and prev_prev_t < 0:
                    img = frames_nearby_times[prev_t]
                    faces = boxes_nearby_times[prev_t]
                    faces = [face.tolist() for face in faces]
                    for face in faces:
                        draw_box(face, img, args.shape, white_color)
                    assert img.shape == (height, width, 3), f'img.shape = {img.shape}, height = {height}, width = {width}'
                    writer.write(img)
                    del frames_nearby_times[prev_t]

                else:
                    prev_prev_boxes = boxes_nearby_times[prev_prev_t]
                    prev_boxes = boxes_nearby_times[prev_t]    
                    this_boxes = boxes_nearby_times[this_t]

                    img = frames_nearby_times[prev_t]
                    faces = boxes_nearby_times[prev_t]
                    faces = [face.tolist() for face in faces]
                    if len(faces) != 2:
                        pass
                    for face in faces:
                        draw_box(face, img, args.shape, white_color)
                    assert img.shape == (height, width, 3), f'img.shape = {img.shape}, height = {height}, width = {width}'
                    writer.write(img)
                    del frames_nearby_times[prev_t]
            else:
                if prev_t>=0:
                    img=frames_nearby_times[prev_t]
                    assert img.shape == (height, width, 3), f'img.shape = {img.shape}, height = {height}, width = {width}'
                    writer.write(img)
                    del frames_nearby_times[prev_t]

            #     # if face detected
            #         # compute similarity
            #     # if found similar or faces not detected
            #         # blur all the faces present in that frame 
    except KeyboardInterrupt:
        print(temp)



            

            

