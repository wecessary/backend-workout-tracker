from app import db
from app import User, Workout, Exercise, Sets

uid1 = "3uxwTAoNZsNqIfrCyCHyDCaxmIq1"
uid2 = "RNKexcaal8UhWQfOkYoSG73ozcG3"

uids = [uid1, uid2]


def init_db(uids):
    for count, uid in enumerate(uids):
        user = User(firebase_uid=uid, name=f"user{count + 1}")
        workout1 = Workout(workout_date="2022-10-03", user=user)
        exercise1 = Exercise(exercise_name="biceps",
                             workout=workout1, index=0, comment=f"I am totally user {count + 1}",
                             )
        set1 = Sets(index=0, reps=10, weight=15, easy=True, done=False,
                    exercise=exercise1)
        set2 = Sets(index=1, reps=11, weight=16, easy=True, done=False,
                    exercise=exercise1)

        db.session.add(user)
        db.session.add(workout1)
        db.session.add(exercise1)
        db.session.add_all([set1, set2])
        db.session.commit()
