from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Robot, Base, Part, User

engine = create_engine('sqlite:///robotparts.db')

DBSession = sessionmaker(bind=engine)
session = DBSession()

User1 = User(name="Mike", email="iamnot@robot.com",
             picture='http://rlv.zcache.com/i_am_not_a_robot_button-r19df8f94fc4b455daf737cf5cdcbbccd_x7j3i_8byvr_324.jpg')
session.add(User1)
session.commit()


robot01 = Robot(user_id=1, name="Hannah")

session.add(robot01)
session.commit()


robot02 = Robot(user_id=1, name="Lone Wanderer")

session.add(robot02)
session.commit()
