from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from functools import wraps
import firebase_admin
from firebase_admin import credentials, auth
import datetime

now = datetime.datetime.now()
now_as_string = now.strftime("%Y-%m-%d")

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
        except Exception as e:
            return {
                       "message": "Something went wrong",
                       "data": None,
                       "error": str(e)
                   }, 500
        return f(uid, *args, **kwargs)

    return decorated


def add_new_user(uids):
    for count, uid in enumerate(uids):
        user = User(firebase_uid=uid, name=f"user{count + 1}")
        workout1 = Workout(workout_date=now_as_string, user=user)
        exercise1 = Exercise(exercise_name="",
                             workout=workout1, index=0, comment=f"",
                             )
        set1 = Sets(index=0, reps=10, weight=15, easy=True, done=False,
                    exercise=exercise1)

        db.session.add(user)
        db.session.add(workout1)
        db.session.add(exercise1)
        db.session.add(set1)
        db.session.commit()


@app.route("/", methods=["GET", "PUT"])
@token_required
def api_user(uid):
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

    def update_user(uid):
        user = User.query.filter_by(firebase_uid=uid).first()

        def update_sets(i_exercise, exercise):
            for i_set, set in enumerate(exercise.sets):
                sets_from_response = request.json["workoutData"][i_exercise]["sets"]
                exercise.sets[i_set].reps = sets_from_response[i_set]["reps"]
                exercise.sets[i_set].weight = sets_from_response[i_set]["weight"]
                exercise.sets[i_set].easy = sets_from_response[i_set]["easy"]
                exercise.sets[i_set].true = sets_from_response[i_set]["done"]

        def update_exercises(workout):
            for i_exercise, exercise in enumerate(workout.exercises):
                workout.exercises[i_exercise].exercise_name = request.json["workoutData"][i_exercise]["name"]
                workout.exercises[i_exercise].comment = request.json["workoutData"][i_exercise]["comment"]
                update_sets(i_exercise, exercise)

        for workout in user.workouts:
            if workout.workout_date == request.json["date"]:
                update_exercises(workout)
                db.session.commit()

        return get_user_data(user)

    if request.method == "GET":
        user = User.query.filter_by(firebase_uid=uid).first()
        if user:
            return get_user_data(user), 200
        else:
            add_new_user([uid])
            new_user = User.query.filter_by(firebase_uid=uid).first()
            return get_user_data(new_user), 200

    if request.method == "PUT":
        return update_user(uid), 400


if __name__ == "__main__":
    app.run(debug=True)
