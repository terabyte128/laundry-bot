from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Machine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    last_reading = db.Column(db.Float, nullable=False, default=0)
    updated_at = db.Column(db.Integer, nullable=False, default=0)
    loads = db.relationship("Load", backref="machine", lazy="dynamic")


class Roommate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    loads = db.relationship("Load", backref="roommate", lazy="dynamic")


class Load(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(
        db.Integer, db.ForeignKey("machine.id"), nullable=False
    )
    roommate_id = db.Column(db.Integer, db.ForeignKey("roommate.id"))
    cycle_number = db.Column(db.Integer, nullable=False, default=1)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    collected = db.Column(db.Boolean, nullable=False, default=False)
