# coding: utf-8
# !/usr/bin/env python3

from flask import Flask, render_template, request, redirect, jsonify, url_for, flash
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Robot, Part, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "RobotCatalog"

engine = create_engine('sqlite:///robotparts.db', connect_args={'check_same_thread': False}, echo=True)
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/login')
def showLogin():
    state = ''.join(
        random.choice(string.ascii_uppercase + string.digits) for x in range(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code, now compatible with Python3
    request.get_data()
    code = request.data.decode('utf-8')

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    # Submit request, parse response - Python3 compatible
    h = httplib2.Http()
    response = h.request(url, 'GET')[1]
    str_response = response.decode('utf-8')
    result = json.loads(str_response)

    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    return output

# User Helper Functions


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

# DISCONNECT - Revoke a current user's token and reset their login_session


@app.route('/gdisconnect')
def gdisconnect():
        # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        # Reset the user's sesson.
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/robots/<int:robot_id>/parts/JSON')
def robotPartsJSON(robot_id):
    robot = session.query(Robot).filter_by(id=robot_id).one()
    parts = session.query(Part).filter_by(
        robot_id=robot_id).all()
    return jsonify(Part=[i.serialize for i in parts])


@app.route('/robots/<int:robot_id>/parts/<int:part_id>/JSON')
def partsJSON(robot_id, part_id):
    robotPart = session.query(Part).filter_by(id=part_id).one()
    return jsonify(robotPart=robotPart.serialize)


@app.route('/robots/JSON')
def robotsJSON():
    robots = session.query(Robot).all()
    return jsonify(robots=[i.serialize for i in robots])


# Show all robots
@app.route('/')
@app.route('/robots/')
def showRobots():
    robots = session.query(Robot).all()
    if 'username' not in login_session:
        return render_template('publicRobots.html', robots=robots)
    else:
    # return "This page will show all my robots"
        return render_template('showRobot.html', robots=robots)


@app.route('/robots/new', methods=['GET', 'POST'])
def newRobot():
    if 'username' not in login_session:
        return redirect('/login')
	if request.method == 'POST':
		newRobot = Robot(name=request.form['name'])
		session.add(newRobot)
		session.commit()
		flash("new robot created!")
		return redirect(url_for('showRobots'))
	else:
		return render_template('newRobot.html')


@app.route('/robots/<int:robot_id>/edit/', methods=['GET', 'POST'])
def editRobot(robot_id):
    editedRobot = session.query(
        Robot).filter_by(id=robot_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        if request.form['name']:
            editedRobot.name = request.form['name']
            return redirect(url_for('showRobots'))
    else:
        return render_template(
            'editRobot.html', robot=editedRobot)

    # return 'This page will be for editing robot %s' % robot_id

# Delete a robot


@app.route('/robots/<int:robot_id>/delete/', methods=['GET', 'POST'])
def deleteRobot(robot_id):
    robotToDelete = session.query(
        Robot).filter_by(id=robot_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        session.delete(robotToDelete)
        session.commit()
        return redirect(
            url_for('showRobots', robot_id=robot_id))
    else:
        return render_template(
            'deleteRobot.html', robot=robotToDelete)
    # return 'This page will be for deleting robot %s' % robot_id


# Show a robot parts
@app.route('/robots/<int:robot_id>/')
@app.route('/robots/<int:robot_id>/parts/')
def showParts(robot_id):
    robot = session.query(Robot).filter_by(id=robot_id).one()
    parts = session.query(Part).filter_by(
        robot_id=robot_id).all()
    return render_template('parts.html', parts=parts, robot=robot)
    # return 'This page is the parts for robot %s' % robot_id

# Create a new menu item


@app.route('/robots/<int:robot_id>/parts/new/', methods=['GET', 'POST'])
def newPart(robot_id):
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newPart = Part(name=request.form['name'], description=request.form[
                           'description'], price=request.form['price'], material=request.form['material'], robot_id=robot_id)
        session.add(newPart)
        session.commit()

        return redirect(url_for('showParts', robot_id=robot_id))
    else:
        return render_template('newParts.html', robot_id=robot_id)

    return render_template('newParts.html', robot=robot)
    # return 'This page is for making a new menu item for robot %s'
    # %robot_id

# Edit a menu item


@app.route('/robots/<int:robot_id>/parts/<int:part_id>/edit',
           methods=['GET', 'POST'])
def editPart(robot_id, part_id):
    editedPart = session.query(Part).filter_by(id=part_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        if request.form['name']:
            editedPart.name = request.form['name']
        if request.form['description']:
            editedPart.description = request.form['description']
        if request.form['price']:
            editedPart.price = request.form['price']
        if request.form['material']:
            editedPart.material = request.form['material']
        session.add(editedPart)
        session.commit()
        return redirect(url_for('showParts', robot_id=robot_id))
    else:

        return render_template(
            'editPart.html', robot_id=robot_id, part_id=part_id, part=editedPart)

    # return 'This page is for editing menu item %s' % menu_id

# Delete a menu item


@app.route('/robots/<int:robot_id>/parts/<int:part_id>/delete',
           methods=['GET', 'POST'])
def deletePart(robot_id, part_id):
    partToDelete = session.query(Part).filter_by(id=part_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        session.delete(partToDelete)
        session.commit()
        return redirect(url_for('showParts', robot_id=robot_id))
    else:
        return render_template('deletePart.html', part=partToDelete)
    # return "This page is for deleting menu item %s" % menu_id


if __name__ == '__main__':
	app.secret_key = 'super_secret_key'
	app.debug = True
	app.run(host = '0.0.0.0', port = 8000)