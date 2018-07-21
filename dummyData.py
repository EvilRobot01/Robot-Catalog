from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Robot, Base, Part

engine = create_engine('sqlite:///robotparts.db')

DBSession = sessionmaker(bind=engine)
session = DBSession()


robot01 = Robot(name="Hannah")

session.add(robot01)
session.commit()


robot02 = Robot(name="Lone Wanderer")

session.add(robot02)
session.commit()
