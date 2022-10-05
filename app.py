from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from functools import wraps
import firebase_admin
from firebase_admin import credentials, auth

# create the extension
db = SQLAlchemy()
# create the app
app = Flask(__name__)
# configure the SQLite database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
# initialize the app with the extension
db.init_app(app)
ma = Marshmallow(app)

cred = credentials.Certificate("fb_admin_config.json")
firebase_admin.initialize_app(cred)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.String(db.String)
    firebase_uid = db.Column(db.String, unique=True)
    workouts = db.relationship("Workout", backref="user")


class Workout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    workout_date = db.Column(db.String)
    exercises = db.relationship("Exercise", backref="workout")
    user_id = db.Column(db.String, db.ForeignKey("user.id"))


class Exercise(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    index = db.Column(db.Integer)  # nth exercise of the day e.g. bicep curls
    exercise_name = db.Column(db.String)
    sets = db.relationship("Sets", backref="exercise")
    workout_id = db.Column(db.String, db.ForeignKey("workout.id"))
    comment = db.Column(db.Text)


class Sets(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    index = db.Column(db.Integer)  # nth set of the day e.g. 2nd set of bicep curls
    reps = db.Column(db.Integer)
    weight = db.Column(db.Integer)
    easy = db.Column(db.Boolean)
    done = db.Column(db.Boolean)
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercise.id"))


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[1]
        if not token:
            return jsonify({"message": "Token is missing.",
                            "error": "Unauthorized"}), 401
        try:
            decoded_token = auth.verify_id_token(token)
            uid = decoded_token['uid']
            user = User.query.filter_by(firebase_uid=uid).first()
        except Exception as e:
            return {
                       "message": "Something went wrong",
                       "data": None,
                       "error": str(e)
                   }, 500
        return f(user, *args, **kwargs)

    return decorated


@app.route("/", methods=["GET", "PUT"])
@token_required
def api_user(user):
    def get_sets(exercise):
        sets = []
        for set in exercise.sets:
            set_object = {"index": set.index,
                          "reps": set.reps,
                          "weight": set.weight,
                          "easy": set.easy,
                          "done": set.done
                          }
            sets.append(set_object)
        return sets

    def get_exercises(workout):
        exercises = []
        for exercise in workout.exercises:
            exercise_obj = {"index": exercise.index,
                            "name": exercise.exercise_name,
                            "comment": exercise.comment,
                            "sets": get_sets(exercise)
                            }
            exercises.append(exercise_obj)
        return exercises

    def get_user_data(user):
        user_data = []
        for workout in user.workouts:
            workout_object = {"date": workout.workout_date, "workoutData": get_exercises(workout)}
            user_data.append(workout_object)
        return user_data

    def update_user(user):
        def update_sets(i_exercise, exercise):
            for i_set, set in enumerate(exercise.sets):
                sets_from_response = request.json["workoutData"][i_exercise]["sets"]
                exercise.sets[i_set].reps = sets_from_response[i_set]["reps"]
                exercise.sets[i_set].weight = sets_from_response[i_set]["weight"]
                exercise.sets[i_set].easy = sets_from_response[i_set]["easy"]
                exercise.sets[i_set].true = sets_from_response[i_set]["done"]

        def update_exercises(workout):
            for i_exercise, exercise in enumerate(workout.exercises):
                print("printed!:", request.json["workoutData"][i_exercise])
                workout.exercises[i_exercise].exercise_name = request.json["workoutData"][i_exercise]["name"]
                workout.exercises[i_exercise].comment = request.json["workoutData"][i_exercise]["comment"]
                update_sets(i_exercise, exercise)

        for workout in user.workouts:
            if workout.workout_date == request.json["date"]:
                update_exercises(workout)
                db.session.commit()

        return get_user_data(user)

    if request.method == "GET":
        return get_user_data(user), 200
    if request.method == "PUT":
        return update_user(user), 400


# @app.route("/update-user-data")
# @token_required
# def update_user(user):
#     def update_sets(i_exercise, exercise):
#         for i_set, set in enumerate(exercise.sets):
#             sets_from_response = request.json["workoutData"][i_exercise]["sets"]
#             exercise.sets[i_set].reps = sets_from_response[i_set]["reps"]
#             exercise.sets[i_set].weight = sets_from_response[i_set]["weight"]
#             exercise.sets[i_set].easy = sets_from_response[i_set]["easy"]
#             exercise.sets[i_set].true = sets_from_response[i_set]["done"]
#
#     def update_exercises(workout):
#         for i_exercise, exercise in enumerate(workout.exercises):
#             print("printed!:", request.json["workoutData"][i_exercise])
#             workout.exercises[i_exercise].exercise_name = request.json["workoutData"][i_exercise]["name"]
#             workout.exercises[i_exercise].comment = request.json["workoutData"][i_exercise]["comment"]
#             update_sets(i_exercise, exercise)
#
#     for workout in user.workouts:
#         if workout.workout_date == request.json["date"]:
#             update_exercises(workout)
#             db.session.commit()
#
#     return get_user_data(user)

# sets = [
#     {"index": user.workouts[0].exercises[0].sets[0].index,
#      "reps": user.workouts[0].exercises[0].sets[0].reps,
#      "weight": user.workouts[0].exercises[0].sets[0].weight,
#      "easy": user.workouts[0].exercises[0].sets[0].easy,
#      "done": user.workouts[0].exercises[0].sets[0].done
#      }]
#
# workoutData = [{
#     "index": user.workouts[0].exercises[0].index,
#     "name": user.workouts[0].exercises[0].exercise_name,
#     "comment": user.workouts[0].exercises[0].comment,
#     "sets": sets}]
#
# user_data = [
#     {"date": user.workouts[0].workout_date, "workoutData": workoutData}
# ]
# return user_data, 200


if __name__ == "__main__":
    app.run(debug=True)
