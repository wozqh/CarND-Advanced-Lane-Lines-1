import numpy as np
import cv2
from line import *
from preprocess import use_color

class Lane():
    def __init__(self, MInv):
        self.leftx = None
        self.lefty = None
        self.rightx = None
        self.righty = None
        self.binary_warped = None
        self.left_line = Line('left')
        self.right_line = Line('right')
        self.redetect = True
        self.redetect_cnt = 0
        self.MInv = MInv
        self.margin = 60
        self.left_fit = None
        self.right_fit = None
        self.offset = None
        self.left_bestx = None
        self.right_bestx = None
        self.left_radius_of_curvature = None
        self.right_radius_of_curvature = None
        self.valid_both_lanes_cnt = 0
        self.minpix = 80
        self.left_confidence = True
        self.right_confidence = True
        self.distance_queue = deque(maxlen=10)
        self.use_color = True

    def find_lane(self):
        # Assuming you have created a warped binary image called "binary_warped"
        # Take a histogram of the bottom half of the image
        histogram = np.sum(self.binary_warped[self.binary_warped.shape[0] // 2:, :], axis=0)
        # Create an output image to draw on and  visualize the result
        # out_img = np.dstack((binary_warped, binary_warped, binary_warped)) * 255
        # Find the peak of the left and right halves of the histogram
        # These will be the starting point for the left and right lines
        midpoint = np.int(histogram.shape[0] / 2)
        leftx_base = np.argmax(histogram[:midpoint])
        rightx_base = np.argmax(histogram[midpoint:]) + midpoint

        # Choose the number of sliding windows
        nwindows = 9
        # Set height of windows
        window_height = np.int(self.binary_warped.shape[0] / nwindows)
        # Identify the x and y positions of all nonzero pixels in the image
        nonzero = self.binary_warped.nonzero()
        nonzeroy = np.array(nonzero[0])
        nonzerox = np.array(nonzero[1])
        # Current positions to be updated for each window
        leftx_current = leftx_base
        rightx_current = rightx_base
        # Set the width of the windows +/- margin
        margin = self.margin
        # Set minimum number of pixels found to recenter window
        minpix = self.minpix
        maxpix = margin * self.binary_warped.shape[0]
        # Create empty lists to receive left and right lane pixel indices
        left_lane_inds = []
        right_lane_inds = []
        left_hit = 0
        right_hit = 0
        # Step through the windows one by one
        for window in range(nwindows):
            # Identify window boundaries in x and y (and right and left)
            win_y_low = self.binary_warped.shape[0] - (window + 1) * window_height
            win_y_high = self.binary_warped.shape[0] - window * window_height
            win_xleft_low = leftx_current - margin
            win_xleft_high = leftx_current + margin
            win_xright_low = rightx_current - margin
            win_xright_high = rightx_current + margin
            good_left_inds = ((nonzeroy >= win_y_low) & (nonzeroy < win_y_high) &
                              (nonzerox >= win_xleft_low) & (nonzerox < win_xleft_high)).nonzero()[0]
            good_right_inds = ((nonzeroy >= win_y_low) & (nonzeroy < win_y_high) &
                               (nonzerox >= win_xright_low) & (nonzerox < win_xright_high)).nonzero()[0]
            # Append these indices to the lists
            left_lane_inds.append(good_left_inds)
            right_lane_inds.append(good_right_inds)
            # If you found > minpix pixels, recenter next window on their mean position
            good_left_inds_len = len(good_left_inds)
            good_right_inds_len = len(good_right_inds)
            print('good inds len ', good_left_inds_len, good_right_inds_len)
            if good_left_inds_len > minpix:
                left_hit += 1
                leftx_current = np.int(np.mean(nonzerox[good_left_inds]))
            if good_right_inds_len > minpix:
                right_hit += 1
                rightx_current = np.int(np.mean(nonzerox[good_right_inds]))

        if left_hit < 2 or right_hit < 2:
            self.redetect = True
            return
        # Concatenate the arrays of indices
        left_lane_inds = np.concatenate(left_lane_inds)
        right_lane_inds = np.concatenate(right_lane_inds)
        leftx = nonzerox[left_lane_inds]
        rightx = nonzerox[right_lane_inds]
        middle = (np.mean(rightx) + np.mean(leftx)) / 2
        lane_margin = 0
        if 100 < abs(650 - middle):
            print("find_lane distance failed:{:>.2f}".format(middle))
            return

        # Extract left and right line pixel positions
        self.leftx = leftx #nonzerox[left_lane_inds]
        self.lefty = nonzeroy[left_lane_inds]
        self.rightx = rightx #nonzerox[right_lane_inds]
        self.righty = nonzeroy[right_lane_inds]

        return self.leftx, self.lefty, self.rightx, self.righty

    def find_lane_skip_window(self):
        nonzero = self.binary_warped.nonzero()
        nonzeroy = np.array(nonzero[0])
        nonzerox = np.array(nonzero[1])
        margin = self.margin

        left_fit = self.left_fit
        right_fit = self.right_fit

        if left_fit is None or right_fit is None:
            return None, 0, 0, None, None

        left_lane_inds = ((nonzerox > (left_fit[0] * (nonzeroy ** 2) + left_fit[1] * nonzeroy +
                        left_fit[2] - margin)) & (nonzerox < (left_fit[0] * (nonzeroy ** 2) +
                        left_fit[1] * nonzeroy + left_fit[2] + margin)))

        right_lane_inds = ((nonzerox > (right_fit[0] * (nonzeroy ** 2) + right_fit[1] * nonzeroy +
                        right_fit[2] - margin)) & (nonzerox < (right_fit[0] * (nonzeroy ** 2) +
                        right_fit[1] * nonzeroy + right_fit[2] + margin)))

        minpix = self.minpix * 9
        leftx = nonzerox[left_lane_inds]
        rightx = nonzerox[right_lane_inds]
        if len(leftx) < minpix or len(rightx) < minpix:
            return

        # Again, extract left and right line pixel positions
        self.leftx = nonzerox[left_lane_inds]
        self.lefty = nonzeroy[left_lane_inds]
        self.rightx = nonzerox[right_lane_inds]
        self.righty = nonzeroy[right_lane_inds]


        return self.leftx, self.lefty, self.rightx, self.righty

    def show_lane(self):
        binary_warped = self.binary_warped
        left_fit = self.left_fit
        right_fit = self.right_fit
        margin = self.margin

        if self.left_fit is None or self.right_fit is None:
            return np.dstack((binary_warped, binary_warped, binary_warped)) * 255
        # print('left_fit', left_fit)
        # print('right_fit', right_fit)
        # Generate x and y values for plotting
        ploty = np.linspace(0, binary_warped.shape[0] - 1, binary_warped.shape[0])
        left_fitx = left_fit[0] * ploty ** 2 + left_fit[1] * ploty + left_fit[2]
        right_fitx = right_fit[0] * ploty ** 2 + right_fit[1] * ploty + right_fit[2]

        # Create an image to draw on and an image to show the selection window
        out_img = np.dstack((binary_warped, binary_warped, binary_warped)) * 255
        window_img = np.zeros_like(out_img)
        # Color in left and right line pixels
        out_img[self.lefty, self.leftx] = [255, 0, 0]
        out_img[self.righty, self.rightx] = [0, 0, 255]

        # Generate a polygon to illustrate the search window area
        # And recast the x and y points into usable format for cv2.fillPoly()
        # when you are drawing a polygon you need to give points in a consecutive
        # manner so you go from left bottom to left top and then you need to go from
        # right TOP to right BOTTOM. Hence you need to flip the right side polynomial
        # to make them go from top to bottom.
        left_line_window1 = np.array([np.transpose(np.vstack([left_fitx - margin, ploty]))])
        left_line_window2 = np.array([np.flipud(np.transpose(np.vstack([left_fitx + margin, ploty])))])
        left_line_pts = np.hstack((left_line_window1, left_line_window2))
        right_line_window1 = np.array([np.transpose(np.vstack([right_fitx - margin, ploty]))])
        right_line_window2 = np.array([np.flipud(np.transpose(np.vstack([right_fitx + margin, ploty])))])
        right_line_pts = np.hstack((right_line_window1, right_line_window2))

        # Draw the lane onto the warped blank image
        cv2.fillPoly(window_img, np.int_([left_line_pts]), (0, 255, 0))
        cv2.fillPoly(window_img, np.int_([right_line_pts]), (0, 255, 0))
        result = cv2.addWeighted(out_img, 1, window_img, 0.3, 0)

        return result

    def project_back(self, orig):
        if self.MInv is None or self.left_fit is None or self.right_fit is None:
            return orig
        binary_warped = self.binary_warped
        left_fit = self.left_fit
        right_fit = self.right_fit
        # Generate x and y values for plotting
        ploty = np.linspace(0, binary_warped.shape[0] - 1, binary_warped.shape[0])
        left_fitx = left_fit[0] * ploty ** 2 + left_fit[1] * ploty + left_fit[2]
        right_fitx = right_fit[0] * ploty ** 2 + right_fit[1] * ploty + right_fit[2]

        # Create an image to draw the lines on
        warp_zero = np.zeros_like(binary_warped).astype(np.uint8)
        color_warp = np.dstack((warp_zero, warp_zero, warp_zero))

        # Recast the x and y points into usable format for cv2.fillPoly()
        pts_left = np.array([np.transpose(np.vstack([left_fitx, ploty]))])
        pts_right = np.array([np.flipud(np.transpose(np.vstack([right_fitx, ploty])))])
        pts = np.hstack((pts_left, pts_right))

        # Draw the lane onto the warped blank image
        cv2.fillPoly(color_warp, np.int_([pts]), (0, 255, 0))

        # Warp the blank back to original image space using inverse perspective matrix (Minv)
        newwarp = cv2.warpPerspective(color_warp, self.MInv, (orig.shape[1], orig.shape[0]))
        # Combine the result with the original image
        result = cv2.addWeighted(orig, 1, newwarp, 0.3, 0)
        return result

    def fit_lane(self, warped_img):
        if self.redetect_cnt > 5:
            self.redetect_cnt -= 1
            self.redetect = True

        self.binary_warped = warped_img
        if self.redetect:
            self.use_color = not self.use_color
            use_color(self.use_color)
            print('fit_lane redetect')
            self.distance_queue.clear()
            self.find_lane()
            try:
                len_right = len(self.rightx)
            except:
                len_right = 0
            try:
                len_left = len(self.leftx)
            except:
                len_left = 0
            # if len_left == 0 and len_right != 0:
            #     print('cannot find left')
            #     self.leftx = self.rightx - 500
            #     self.lefty = self.righty
            # elif len_right == 0 and len_left != 0:
            #     print('cannot find right')
            #     self.rightx = self.leftx + 500
            #     self.righty = self.lefty
            if len_left == 0 or len_right == 0:
                print('cannot find both')
                z = np.zeros_like(warped_img)
                out_img = np.dstack((z, z, z)) * 255
                return np.zeros_like(warped_img)
        else:
            # self.find_lane()
            self.find_lane_skip_window()
        self.redetect = False
        # self.find_lane()
        redetect = self.fitxy()
        # if not redetect:
        try:
            self.offset = self.left_line_base_pos + self.right_line_base_pos
            self.left_fit, self.right_fit = self.fit_smoothing(self.left_line, self.right_line)
            print('left best fit: {:>9.4} {:>9.4} {:>9.4}'.format(self.left_fit[0], self.left_fit[1], self.left_fit[2]))
            print('right best fit: {:>9.4} {:>9.4} {:>9.4}'.format(self.right_fit[0], self.right_fit[1], self.right_fit[2]))
            print('offset: {:>9.4} {:>9.4} {:>9.4}'.format(self.left_line_base_pos, self.right_line_base_pos, self.offset))
            print('curvature: {:>9.4} {:>9.4}'.format(self.left_radius_of_curvature, self.right_radius_of_curvature))
        except:
            print('offset', None)
        # self.fit =

        return self.show_lane()

    def fitxy(self):
        left_val = self.left_line.valid_xy(self.leftx, self.lefty)
        right_val = self.right_line.valid_xy(self.rightx, self.righty)


        if left_val:
            self.left_bestx, self.left_line_base_pos, self.left_radius_of_curvature, _ = self.left_line.fit_xy()
        else:
            if self.left_line.re_detected():
                self.left_confidence = False
                self.redetect = True
        if right_val:
            self.right_bestx, self.right_line_base_pos, self.right_radius_of_curvature, _ = self.right_line.fit_xy()
        else:
            if self.right_line.re_detected():
                self.right_confidence = False
                self.redetect = True
        return self.redetect

    def get_lane_prop(self):
        return self.offset, self.left_bestx, self.right_bestx, self.left_radius_of_curvature, self.right_radius_of_curvature


    def make_fake_line(self, left_line, right_line):
        if self.left_confidence and self.right_confidence:
            return 1#both confident, use best_fit
        max_y = self.binary_warped.shape[0]
        valid_y = np.array([max_y, max_y // 2, 0])
        if len(self.distance_queue) > 0:
            lane_space = np.mean(self.distance_queue, axis=0)
        else:
            lane_space = [600, 600, 600, 650]
        margin = [150, 150, 150, 100]

        left_fit = left_line.current_fit
        right_fit = right_line.current_fit
        left_fitx = left_fit[0] * valid_y ** 2 + left_fit[1] * valid_y + left_fit[2]
        right_fitx = right_fit[0] * valid_y ** 2 + right_fit[1] * valid_y + right_fit[2]
        current_middle = (left_fitx[0] + right_fitx[0]) / 2
        lane_current_distance = abs(right_fitx - left_fitx)
        lane_current_distance = np.append(lane_current_distance, current_middle)
        avg_distance = np.mean(lane_current_distance[:-1])
        abandon_current_fit = False
        for i, distance in enumerate(lane_current_distance[:-1]):
            if abs(avg_distance - distance) > 200:
                abandon_current_fit = True
                break
            # if distance > (lane_space[i] + margin[i]) or distance < (lane_space[i] - margin[i]):
            #     abandon_current_fit = True
            #     break


        gap = np.mean(lane_space)
        if abandon_current_fit and self.redetect_cnt < 2:
            self.distance_queue.append(lane_current_distance * 0.7 + np.array([600, 600, 600, 650]) * 0.3)
            return 3
            # if self.left_confidence:
            #     print('make right fake')
            #     self.right_confidence = True
            #     self.rightx = self.leftx + gap #TODO: out of range
            #     self.righty = self.lefty
            #     self.right_line.clean_deque()
            #     self.fitxy()
            #     return 2 #don't need valid both
            # elif self.right_confidence:
            #     print('make left fake')
            #     self.left_confidence = True
            #     self.leftx = self.rightx - gap #TODO: out of range
            #     self.lefty = self.righty
            #     self.left_line.clean_deque()
            #     self.fitxy()
            #     return 2
            # else:
            #     # self.left_line.clean_deque()
            #     # self.right_line.clean_deque()
            #     self.redetect = True
            #     return 3 # redetect
        else:
            self.left_confidence = True
            self.right_confidence = True
            self.left_line.last_fit = self.left_line.current_fit
            self.right_line.last_fit = self.right_line.current_fit
            return 0 #use last fit


    def valid_both_lanes(self, left_line, right_line):
        ret = self.make_fake_line(left_line, right_line)
        if ret == 0:
            return True, self.left_line.current_fit, self.right_line.current_fit
        if ret == 3:
            return False, self.left_fit, self.right_fit
        elif ret == 2:
            return True, self.left_line.best_fit, self.right_line.best_fit


        max_y = self.binary_warped.shape[0]
        valid_y = np.array([max_y, max_y//2, 0])
        if len(self.distance_queue) > 0:
            lane_space = np.mean(self.distance_queue, axis=0)
        else:
            lane_space = [600, 600, 600, 650]
        margin = [150, 250, 350, 100]
        bad_current_margin = [150,200,250,80]
        good_current_margin = [130, 180, 230, 80]

        left_fit = left_line.best_fit
        right_fit = right_line.best_fit

        left_fitx = left_fit[0] * valid_y ** 2 + left_fit[1] * valid_y + left_fit[2]
        right_fitx = right_fit[0] * valid_y ** 2 + right_fit[1] * valid_y + right_fit[2]
        best_middle = (left_fitx[0] + right_fitx[0]) / 2
        lane_best_distance = right_fitx - left_fitx
        lane_best_distance = np.append(lane_best_distance, best_middle)

        left_fit = left_line.current_fit
        right_fit = right_line.current_fit
        left_fitx = left_fit[0] * valid_y ** 2 + left_fit[1] * valid_y + left_fit[2]
        right_fitx = right_fit[0] * valid_y ** 2 + right_fit[1] * valid_y + right_fit[2]
        current_middle = (left_fitx[0] + right_fitx[0]) / 2
        lane_current_distance = right_fitx - left_fitx
        lane_current_distance = np.append(lane_current_distance, current_middle)

        print('lane_current_distance', lane_current_distance, lane_current_distance-lane_space)
        print('lane_best_distance', lane_best_distance, lane_best_distance-lane_space)
        lane_distance = lane_current_distance * 0.5 + lane_best_distance * 0.5
        self.distance_queue.append(lane_distance * 0.7 + np.array([600, 600, 600, 650])*0.3)
        print('lane_distance', lane_distance)



        left_fit = left_line.best_fit
        right_fit = right_line.best_fit
        valid = True
        abandon_bad_current_fit = False
        current_margin = bad_current_margin
        for i, distance in enumerate(lane_current_distance):
            if distance < 0 or distance > (lane_space[i] + current_margin[i]) \
                    or distance < (lane_space[i] - current_margin[i]):
                abandon_bad_current_fit = True
                break

        if abandon_bad_current_fit:
            abandon_good_current_fit = True
        else:
            print("Check bad_current_margin passed")
            abandon_good_current_fit = False
            current_margin = good_current_margin
            for i, distance in enumerate(lane_current_distance):
                if distance < 0  or distance > (lane_space[i] + current_margin[i]) \
                        or distance < (lane_space[i] - current_margin[i]):
                    abandon_good_current_fit = True
                    break

        if abandon_good_current_fit:
            print("Check good current margin failed")
            print("FIT: using best fit")
            self.left_line.last_fit = self.left_line.best_fit
            self.right_line.last_fit = self.right_line.best_fit
            self.redetect_cnt += 1
            # return valid, left_fit, right_fit
        else:
            if left_line.unvalid_cnt == 0:
                left_fit = left_line.current_fit
            if right_line.unvalid_cnt == 0:
                right_fit = right_line.current_fit
            valid = True
            if self.redetect_cnt > 0:
                self.redetect_cnt -= 1
            print("FIT: using current_fit")

        # for i, distance in enumerate(lane_distance):
        #     if distance > (lane_space[i] + margin[i]) or distance < (lane_space[i] - margin[i]):
        #         left_fit = self.left_fit
        #         right_fit = self.right_fit
        #         valid = False
        #         print("FIT: using last fit")
        #         if self.valid_both_lanes_cnt < 3:
        #             self.valid_both_lanes_cnt += 1
        #             print("valid_both_lines failed")
        #             break
        #         else:
        #             print('valid_both_lines failed, but use the failed fit')
        #             break;
        #
        # if self.valid_both_lanes_cnt > 0:
        #     self.valid_both_lanes_cnt -= 1

        print('valid_both_lines success')
        return valid, left_fit, right_fit

    def fit_smoothing(self, left_line, right_line):
        # left_weight = np.array(left_line.n_x_deque)
        # right_weight = np.array(right_line.n_x_deque)
        # left_fit = np.array(left_line.fit_deque)
        # right_fit = np.array(right_line.fit_deque)
        # n_left = len(left_weight)
        # n_right = len(right_weight)
        # gap = abs(n_left - n_right)
        # if gap != 0:
        #     if n_left < n_right:
        #         left_weight = np.append(left_weight, np.zeros(gap))
        #         left_fit = np.append(left_fit, np.zeros((gap, 3)), axis=0)
        #     else:
        #         right_weight = np.append(right_weight, np.zeros(gap))
        #         right_fit = np.append(right_fit, np.zeros(gap, 3), axis=0)
        #
        # left_w = left_weight / (left_weight + right_weight)
        # left_w = left_w.reshape((-1, 1))
        # right_w = right_weight / (left_weight + right_weight)
        # right_w = right_w.reshape((-1, 1))
        # left_fit = left_fit[:, :-1]
        # right_fit = right_fit[:, :-1]
        # left_fit = left_fit * left_w
        # right_fit = right_fit * right_w
        # both_fit = left_fit + right_fit
        # both_fit = np.mean(both_fit, axis=0, dtype=np.float32)
        # left_best_fit = np.append(both_fit, left_line.best_fit[2])
        # right_best_fit = np.append(both_fit, right_line.best_fit[2])

        # left_weight = np.mean(left_line.n_x_deque)
        # right_weight = np.mean(right_line.n_x_deque)
        # left_fit = left_line.best_fit
        # right_fit = right_line.best_fit
        # print('left best fit: {:>9.4} {:>9.4} {:>9.4}'.format(self.left_fit[0], self.left_fit[1], self.left_fit[2]))
        # print('right best fit: {:>9.4} {:>9.4} {:>9.4}'.format(self.right_fit[0], self.right_fit[1], self.right_fit[2]))
        # left_w = left_weight / (left_weight + right_weight)
        # right_w = right_weight / (left_weight + right_weight)
        # print('left_weight: {:>9.4}'.format(left_w))
        # print('right_weight: {:>9.4}'.format(right_w))
        # left_fit1 = left_fit[:-1] * left_w
        # right_fit1 = right_fit[:-1] * right_w
        # both_fit = left_fit1 + right_fit1
        # print('left best fit1: {:>9.4} {:>9.4}'.format(left_fit1[0], left_fit1[1]))
        # print('right best fit1: {:>9.4} {:>9.4}'.format(right_fit1[0], right_fit1[1]))
        # l_c = self.left_line.best_fit[2]
        # r_c = self.right_line.best_fit[2]
        # # l_c = self.offset + 220
        # # r_c = self.offset + 900
        # # l_c = (self.left_line.bestx + self.left_line.best_fit[2]) / 2 + self.offset
        # # r_c = (self.right_line.bestx + self.right_line.best_fit[2]) / 2 + self.offset
        # left_best_fit = np.append(both_fit, l_c)
        # right_best_fit = np.append(both_fit, r_c)
        # print('left fit: {:>9.4} {:>9.4} {:>9.4}'.format(left_best_fit[0], left_best_fit[1], left_best_fit[2]))
        # print('right fit: {:>9.4} {:>9.4} {:>9.4}'.format(right_best_fit[0], right_best_fit[1], right_best_fit[2]))

        try:
            valid, left_fit, right_fit = self.valid_both_lanes(left_line, right_line)
        except:
            valid = False
            left_fit = self.left_fit
            right_fit = self.right_fit
        if valid:
            print('new best_fit')
        else:
            print('last fit')
            self.redetect_cnt += 1

        return left_fit, right_fit

        # return left_best_fit, right_best_fit
        # return left_line.best_fit, right_line.best_fit


def find_lane_cnn(warped):
    # window settings
    window_width = 50
    window_height = 80  # Break image into 9 vertical layers since image height is 720
    margin = 100  # How much to slide left and right for searching

    def window_mask(width, height, img_ref, center, level):
        output = np.zeros_like(img_ref)
        output[int(img_ref.shape[0] - (level + 1) * height):int(img_ref.shape[0] - level * height),
        max(0, int(center - width / 2)):min(int(center + width / 2), img_ref.shape[1])] = 1
        return output

    def find_window_centroids(image, window_width, window_height, margin):

        window_centroids = []  # Store the (left,right) window centroid positions per level
        window = np.ones(window_width)  # Create our window template that we will use for convolutions

        # First find the two starting positions for the left and right lane by using np.sum to get the vertical image slice
        # and then np.convolve the vertical image slice with the window template

        # Sum quarter bottom of image to get slice, could use a different ratio
        l_sum = np.sum(image[int(3 * image.shape[0] / 4):, :int(image.shape[1] / 2)], axis=0)
        l_center = np.argmax(np.convolve(window, l_sum)) - window_width / 2
        r_sum = np.sum(image[int(3 * image.shape[0] / 4):, int(image.shape[1] / 2):], axis=0)
        r_center = np.argmax(np.convolve(window, r_sum)) - window_width / 2 + int(image.shape[1] / 2)

        # Add what we found for the first layer
        window_centroids.append((l_center, r_center))

        # Go through each layer looking for max pixel locations
        for level in range(1, (int)(image.shape[0] / window_height)):
            # convolve the window into the vertical slice of the image
            image_layer = np.sum(
                image[int(image.shape[0] - (level + 1) * window_height):int(image.shape[0] - level * window_height), :],
                axis=0)
            conv_signal = np.convolve(window, image_layer)
            # Find the best left centroid by using past left center as a reference
            # Use window_width/2 as offset because convolution signal reference is at right side of window, not center of window
            offset = window_width / 2
            l_min_index = int(max(l_center + offset - margin, 0))
            l_max_index = int(min(l_center + offset + margin, image.shape[1]))
            l_center = np.argmax(conv_signal[l_min_index:l_max_index]) + l_min_index - offset
            # Find the best right centroid by using past right center as a reference
            r_min_index = int(max(r_center + offset - margin, 0))
            r_max_index = int(min(r_center + offset + margin, image.shape[1]))
            r_center = np.argmax(conv_signal[r_min_index:r_max_index]) + r_min_index - offset
            # Add what we found for that layer
            window_centroids.append((l_center, r_center))

        return window_centroids

    window_centroids = find_window_centroids(warped, window_width, window_height, margin)

    # If we found any window centers
    if len(window_centroids) > 0:

        # Points used to draw all the left and right windows
        l_points = np.zeros_like(warped)
        r_points = np.zeros_like(warped)

        # Go through each level and draw the windows
        for level in range(0, len(window_centroids)):
            # Window_mask is a function to draw window areas
            l_mask = window_mask(window_width, window_height, warped, window_centroids[level][0], level)
            r_mask = window_mask(window_width, window_height, warped, window_centroids[level][1], level)
            # Add graphic points from window mask here to total pixels found
            l_points[(l_points == 255) | ((l_mask == 1))] = 255
            r_points[(r_points == 255) | ((r_mask == 1))] = 255

        # Draw the results
        template = np.array(r_points + l_points, np.uint8)  # add both left and right window pixels together
        zero_channel = np.zeros_like(template)  # create a zero color channel
        template = np.array(cv2.merge((zero_channel, template, zero_channel)), np.uint8)  # make window pixels green
        warpage = np.dstack((warped, warped, warped)) * 255  # making the original road pixels 3 color channels
        output = cv2.addWeighted(warpage, 1, template, 0.5, 0.0)  # overlay the orignal road image with window results

    # If no window centers found, just display orginal road image
    else:
        output = np.array(cv2.merge((warped, warped, warped)), np.uint8)

    return output