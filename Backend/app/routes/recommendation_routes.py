from flask import Blueprint, request, jsonify, send_file
import tempfile
import cv2
import mediapipe as mp
import numpy as np
import os 

recommendation_bp = Blueprint("recommendation", __name__)
mp_pose = mp.solutions.pose

def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba, bc = a - b, c - b
    cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    angle = np.degrees(np.arccos(cosine))
    return angle

def draw_feedback(frame, points, angle, label, color=(0, 255, 0)):
    a, b, c = points
    a = tuple(map(int, a))
    b = tuple(map(int, b))
    c = tuple(map(int, c))
    cv2.line(frame, a, b, color, 2)
    cv2.line(frame, c, b, color, 2)
    cv2.circle(frame, b, 5, (0, 0, 255), -1)
    cv2.putText(frame, f"{label}: {int(angle)}°", (b[0] + 10, b[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

def analyze_form(video_path, output_path):
    try:
        print("Entering the analyze form function")
        pose = mp_pose.Pose()
        cap = cv2.VideoCapture(video_path)
        feedback = []
        min_angle = 180
        min_back_angle = 180
        inSquat = False
        rep = 0
        rep_feedback = {}

        comp = cv2.VideoWriter_fourcc(*'mp4v')
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        out = cv2.VideoWriter(output_path, comp, fps, (width, height))

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(image_rgb)

            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                head = [int(landmarks[8].x * width), int(landmarks[8].y * height)]
                hip = [int(landmarks[24].x * width), int(landmarks[24].y * height)]
                knee = [int(landmarks[26].x * width), int(landmarks[26].y * height)]
                ankle = [int(landmarks[28].x * width), int(landmarks[28].y * height)]
                angle = calculate_angle(hip, knee, ankle)
                back_angle = calculate_angle(head, hip, knee)

                draw_feedback(frame, (hip, knee, ankle), angle, "Knee")
                draw_feedback(frame, (head, hip, knee), back_angle, "Back")

                if angle < 150:
                    inSquat = True
                    if angle < min_angle:
                        min_angle = angle
                    if back_angle < min_back_angle:
                        min_back_angle = back_angle
                
                elif angle > 160 and inSquat:
                    rep += 1
                    if min_angle < 70:
                        rep_feedback[f"Rep {rep}"] = f"Good squat depth ({int(min_angle)} degrees)"
                    else:
                        rep_feedback[f"Rep {rep}"] = f"Your current depth is about {int(min_angle)}, try to go lower than 70 degrees"

                    if back_angle > 160:
                        rep_feedback[f"Rep {rep}"] += " - Good back posture"
                    else:
                        rep_feedback[f"Rep {rep}"] += f" - Back is rounded to about {int(min_back_angle)} degrees, try to get it straighter than 160 degrees"
                    min_angle = 180
                    min_back_angle = 180
                    inSquat = False

                out.write(frame)
                
        cap.release()
        out.release()
        pose.close()
        
        if rep == 0:
            feedback.append("No complete reps detected")
            return feedback

        return rep_feedback

    except Exception as e:
        print(f'An error occured while trying to process the request to analyze gym form {str(e)}')

video_path = None

@recommendation_bp.route("/analyze-form", methods=["POST"])
def analyze():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    global video_path
    
    try:
        file = request.files["file"]
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp.write(file.read())
            tmp_path = tmp.name

        tmp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") 
        tmp_out_path = tmp_out.name
        tmp_out.close()
        video_path = tmp_out_path
        feedback = analyze_form(tmp_path, video_path)
        return jsonify({
            "feedback": feedback, 
            "url": "/recommendation/download-feedback-video"
        })
    
    except Exception as e:
        return jsonify({"error": f"An error occured while trying to analyze form: {str(e)}"}), 500

@recommendation_bp.route("/download-feedback-video", methods=["GET"])
def download_feedback():
    try:
        global video_path

        if video_path and os.path.exists(video_path):
            return send_file(video_path, as_attachment=True)
        else:
            jsonify({"error": "No feedback video found"}), 404

    except Exception as e:
        return jsonify({"error": f"An error occured while trying to download the feedback file: {str(e)}"}), 500